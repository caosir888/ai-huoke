from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import PlatformAccount, User, UserQuota
from app.schemas import BindAccountReq, PlatformAccountResp
from app.services.oauth_service import (
    sign_state, verify_state, build_douyin_authorize_url,
    douyin_exchange_code, douyin_get_user_info,
)
from app.utils.auth import decode_access_token, security

router = APIRouter(prefix="/platform", tags=["platform"])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/accounts/bind", response_model=PlatformAccountResp)
async def bind_account(
    req: BindAccountReq, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bind a platform account via token. For Douyin, use OAuth flow instead."""
    quota_result = await db.execute(select(UserQuota).where(UserQuota.user_id == user.id))
    quota = quota_result.scalar_one_or_none()

    if quota:
        count_result = await db.execute(
            select(PlatformAccount).where(PlatformAccount.user_id == user.id)
        )
        current_count = len(count_result.scalars().all())
        if current_count >= quota.account_limit:
            raise HTTPException(status_code=400, detail=f"当前套餐最多绑定{quota.account_limit}个账号")

    account = PlatformAccount(
        user_id=user.id, platform=req.platform,
        account_name=f"{req.platform}_account_{user.phone[:4]}",
        auth_token=req.auth_token, auth_status="active",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/oauth/douyin/authorize")
async def douyin_authorize(user: User = Depends(get_current_user)):
    """Get Douyin OAuth authorization URL."""
    if not settings.DOUYIN_CLIENT_KEY:
        raise HTTPException(status_code=500, detail="抖音开放平台未配置（缺少 DOUYIN_CLIENT_KEY）")
    state = sign_state(user.id)
    url = build_douyin_authorize_url(state)
    return {"authorize_url": url, "state": state}


@router.get("/oauth/douyin/callback")
async def douyin_callback(code: str, state: str = "", db: AsyncSession = Depends(get_db), scopes: str = ""):
    """Handle Douyin OAuth callback."""
    from urllib.parse import urlencode

    # Verify state
    user_id = verify_state(state)
    if not user_id:
        qs = urlencode({"bind_status": "error", "error": "授权验证失败，请重试"})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/oauth/callback?{qs}")

    # trial.whitelist ONLY flow (no other scopes): just exchange code to complete binding, don't store account
    if scopes.strip() == "trial.whitelist":
        token_data = await douyin_exchange_code(code)
        if "data" in token_data and "access_token" in token_data["data"]:
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/oauth/callback?bind_status=success&platform=douyin&whitelist=1")
        else:
            error_msg = token_data.get("data", {}).get("description", "token exchange failed")
            qs = urlencode({"bind_status": "error", "error": error_msg})
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/oauth/callback?{qs}")

    token_data = await douyin_exchange_code(code)
    data = token_data.get("data", {})
    if "access_token" not in data:
        error_msg = data.get("description", data.get("error_description", "Unknown error"))
        qs = urlencode({"bind_status": "error", "error": error_msg})
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/oauth/callback?{qs}")

    access_token = data["access_token"]
    refresh_token = data.get("refresh_token", "")
    open_id = data.get("open_id", "")
    scope_val = data.get("scope", "")
    expires_in = data.get("expires_in", 1296000)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    account_name = f"douyin_{user_id[:8]}"
    avatar = None
    try:
        user_info = await douyin_get_user_info(access_token, open_id)
        if "data" in user_info:
            info = user_info["data"]
            account_name = info.get("nickname", account_name)
            avatar = info.get("avatar", None)
    except Exception:
        pass

    # Upsert by open_id
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user_id,
            PlatformAccount.platform == "douyin",
            PlatformAccount.open_id == open_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.auth_token = access_token
        existing.refresh_token = refresh_token
        existing.scope = scope_val
        existing.expired_at = expires_at
        existing.account_name = account_name
        existing.avatar = avatar
        existing.auth_status = "active"
    else:
        account = PlatformAccount(
            user_id=user_id, platform="douyin",
            account_name=account_name, avatar=avatar,
            auth_token=access_token, refresh_token=refresh_token,
            open_id=open_id, scope=scope_val,
            auth_status="active", expired_at=expires_at,
        )
        db.add(account)

    await db.commit()
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/oauth/callback?bind_status=success&platform=douyin")


@router.get("/accounts", response_model=list[PlatformAccountResp])
async def list_accounts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlatformAccount).where(PlatformAccount.user_id == user.id)
    )
    return result.scalars().all()


@router.delete("/accounts/{account_id}")
async def unbind_account(
    account_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == account_id, PlatformAccount.user_id == user.id
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    await db.delete(account)
    await db.commit()
    return {"message": "已解绑"}
