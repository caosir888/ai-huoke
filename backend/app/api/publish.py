from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PublishTask, PlatformAccount, User
from app.schemas import CreatePublishTaskReq, PublishTaskResp
from app.services.publisher import Publisher
from app.utils.auth import decode_access_token, security

router = APIRouter(prefix="/publish", tags=["publish"])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    return result.scalar_one_or_none()


@router.post("/tasks", response_model=PublishTaskResp)
async def create_publish_task(
    req: CreatePublishTaskReq, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == req.platform_account_id,
            PlatformAccount.user_id == user.id,
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=400, detail="平台账号不存在")

    if account.auth_status != "active":
        raise HTTPException(status_code=400, detail="平台账号未激活，请重新授权")

    task = PublishTask(
        user_id=user.id, video_url=req.video_url,
        platform_account_id=req.platform_account_id,
        title=req.title, schedule_type=req.schedule_type,
        schedule_time=req.schedule_time,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # If immediate publish, execute now
    if req.schedule_type == "now":
        publisher = Publisher()
        task.status = "publishing"
        await db.commit()
        try:
            result = await publisher.publish(
                platform=account.platform,
                account_id=str(account.id),
                account=account,
                video_path=req.video_url,
                title=req.title,
            )
            task.status = "published" if result["status"] == "published" else task.status
            task.publish_result = result
        except Exception as e:
            task.status = "failed"
            task.publish_result = {"error": str(e)}
        await db.commit()
        await db.refresh(task)

    return task


@router.get("/tasks", response_model=list[PublishTaskResp])
async def list_publish_tasks(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
    status: str | None = None,
):
    q = select(PublishTask).where(PublishTask.user_id == user.id)
    if status:
        q = q.where(PublishTask.status == status)
    q = q.order_by(PublishTask.created_at.desc()).limit(100)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/reschedule/{task_id}")
async def reschedule(
    task_id: str, schedule_time: str, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    result = await db.execute(
        select(PublishTask).where(PublishTask.id == task_id, PublishTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("pending",):
        raise HTTPException(status_code=400, detail="只能修改待发布状态的任务")

    task.schedule_time = datetime.fromisoformat(schedule_time)
    await db.commit()
    return {"message": "已重新排期"}


@router.get("/metrics/{task_id}")
async def get_metrics(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PublishTask).where(PublishTask.id == task_id, PublishTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.metrics
