from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import SendCodeReq, LoginReq, TokenResp, UserResp, UpdateProfileReq
from app.utils.auth import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


# In production, use Redis to store verification codes
MOCK_CODES: dict[str, str] = {}


@router.post("/send-code")
async def send_code(req: SendCodeReq):
    code = "8888"  # Mock: in production integrate with SMS service
    MOCK_CODES[req.phone] = code
    return {"message": "验证码已发送", "debug_code": code}


@router.post("/login", response_model=TokenResp)
async def login(req: LoginReq, db: AsyncSession = Depends(get_db)):
    if MOCK_CODES.get(req.phone) != req.code:
        raise HTTPException(status_code=400, detail="验证码错误")

    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()

    if not user:
        user = User(phone=req.phone, password_hash=hash_password(req.phone))
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Also init quota for new users
    from app.models import UserQuota
    result = await db.execute(select(UserQuota).where(UserQuota.user_id == user.id))
    if not result.scalar_one_or_none():
        db.add(UserQuota(user_id=user.id))
        await db.commit()

    token = create_access_token({"sub": user.id, "phone": user.phone})
    del MOCK_CODES[req.phone]
    return TokenResp(access_token=token)


@router.get("/me", response_model=UserResp)
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/profile", response_model=UserResp)
async def update_profile(
    req: UpdateProfileReq,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.industry is not None:
        user.industry = req.industry
    if req.company_name is not None:
        user.company_name = req.company_name
    await db.commit()
    await db.refresh(user)
    return user
