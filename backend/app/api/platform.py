from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PlatformAccount, User, UserQuota
from app.schemas import BindAccountReq, PlatformAccountResp
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
    return result.scalar_one_or_none()


@router.post("/accounts/bind", response_model=PlatformAccountResp)
async def bind_account(
    req: BindAccountReq, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
