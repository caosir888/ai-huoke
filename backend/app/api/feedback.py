from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User
from app.utils.auth import decode_access_token, security

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackReq(BaseModel):
    rating: int = Field(default=0, ge=0, le=5)
    content: str = Field(..., min_length=1, max_length=500)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    from sqlalchemy import select
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("")
async def submit_feedback(
    req: FeedbackReq,
    user: User = Depends(get_current_user),
):
    # In production: write to database or send to issue tracker
    # For now, log and acknowledge
    return {"message": "反馈已收到", "id": user.id, "rating": req.rating}
