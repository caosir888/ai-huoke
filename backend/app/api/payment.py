from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserQuota
from app.services.payment import PLANS, get_all_plans, create_order
from app.utils.auth import decode_access_token, security

router = APIRouter(prefix="/payment", tags=["payment"])


@router.get("/plans")
async def list_plans():
    return get_all_plans()


from pydantic import BaseModel

class OrderReq(BaseModel):
    plan_key: str

@router.post("/order")
async def place_order(
    req: OrderReq,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    plan_key = req.plan_key
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401)
    if plan_key not in PLANS:
        raise HTTPException(status_code=400, detail="未知套餐")

    order = create_order(payload["sub"], plan_key)
    return order


@router.post("/callback")
async def payment_callback(data: dict, db: AsyncSession = Depends(get_db)):
    """WeChat Pay callback endpoint. Updates user plan upon payment."""
    from app.services.payment import handle_callback
    result = handle_callback(data)
    # In production: validate signature from WeChat Pay, then update user + quota
    return {"return_code": "SUCCESS"}
