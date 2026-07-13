"""
Quota enforcement service. Checks daily/monthly limits on video generation,
publishing, account binding, and storage usage per user plan.
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserQuota, EditTask, PublishTask, PlatformAccount, Material

# Plan defaults — keyed by plan_type
PLAN_LIMITS = {
    "free": {
        "daily_edit": 3,
        "monthly_edit": 30,
        "account_limit": 1,
        "storage_bytes_limit": 1 * 1024**3,  # 1 GB
    },
    "basic": {
        "daily_edit": 10,
        "monthly_edit": 100,
        "account_limit": 5,
        "storage_bytes_limit": 10 * 1024**3,
    },
    "pro": {
        "daily_edit": 50,
        "monthly_edit": 500,
        "account_limit": 20,
        "storage_bytes_limit": 50 * 1024**3,
    },
    "enterprise": {
        "daily_edit": 200,
        "monthly_edit": 2000,
        "account_limit": 100,
        "storage_bytes_limit": 200 * 1024**3,
    },
}


def get_limits_for_user(user: User) -> dict:
    return PLAN_LIMITS.get(user.plan_type, PLAN_LIMITS["free"])


async def get_or_create_quota(db: AsyncSession, user_id: str) -> UserQuota:
    result = await db.execute(select(UserQuota).where(UserQuota.user_id == user_id))
    quota = result.scalar_one_or_none()
    if not quota:
        result_user = await db.execute(select(User).where(User.id == user_id))
        user = result_user.scalar_one_or_none()
        limits = get_limits_for_user(user) if user else PLAN_LIMITS["free"]
        quota = UserQuota(
            user_id=user_id,
            daily_video_count=limits["daily_edit"],
            monthly_video_count=limits["monthly_edit"],
            account_limit=limits["account_limit"],
            storage_bytes_limit=limits["storage_bytes_limit"],
        )
        db.add(quota)
        await db.commit()
        await db.refresh(quota)
    return quota


async def check_edit_quota(db: AsyncSession, user_id: str) -> tuple[bool, str]:
    """Check if user can create more edit tasks today/this month."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return False, "用户不存在"

    limits = get_limits_for_user(user)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    # Count today's edit tasks
    daily_q = select(func.count(EditTask.id)).where(
        EditTask.user_id == user_id,
        EditTask.created_at >= today_start,
    )
    daily_count = (await db.execute(daily_q)).scalar() or 0

    if daily_count >= limits["daily_edit"]:
        return False, f"今日剪辑配额已用完（{limits['daily_edit']}条/天），请明天再试或升级套餐"

    # Count this month's edit tasks
    monthly_q = select(func.count(EditTask.id)).where(
        EditTask.user_id == user_id,
        EditTask.created_at >= month_start,
    )
    monthly_count = (await db.execute(monthly_q)).scalar() or 0

    if monthly_count >= limits["monthly_edit"]:
        return False, f"本月剪辑配额已用完（{limits['monthly_edit']}条/月），请升级套餐"

    return True, ""


async def check_storage_quota(db: AsyncSession, user_id: str, new_bytes: int = 0) -> tuple[bool, str]:
    """Check if user has enough storage space."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return False, "用户不存在"

    limits = get_limits_for_user(user)
    used_q = select(func.coalesce(func.sum(Material.size), 0)).where(
        Material.user_id == user_id,
    )
    used = (await db.execute(used_q)).scalar() or 0

    if used + new_bytes > limits["storage_bytes_limit"]:
        limit_gb = limits["storage_bytes_limit"] / (1024**3)
        used_gb = used / (1024**3)
        return False, f"存储空间不足（已用{used_gb:.1f}GB/{limit_gb:.0f}GB），请清理素材或升级套餐"

    return True, ""


async def check_account_quota(db: AsyncSession, user_id: str) -> tuple[bool, str]:
    """Check if user can bind more platform accounts."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return False, "用户不存在"

    limits = get_limits_for_user(user)
    count_q = select(func.count(PlatformAccount.id)).where(
        PlatformAccount.user_id == user_id,
    )
    current = (await db.execute(count_q)).scalar() or 0

    if current >= limits["account_limit"]:
        return False, f"账号绑定配额已用完（{limits['account_limit']}个），请升级套餐"

    return True, ""


async def get_quota_usage(db: AsyncSession, user_id: str) -> dict:
    """Get current quota usage for a user."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {}

    limits = get_limits_for_user(user)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    daily_used = (await db.execute(
        select(func.count(EditTask.id)).where(
            EditTask.user_id == user_id, EditTask.created_at >= today_start
        )
    )).scalar() or 0

    monthly_used = (await db.execute(
        select(func.count(EditTask.id)).where(
            EditTask.user_id == user_id, EditTask.created_at >= month_start
        )
    )).scalar() or 0

    storage_used = (await db.execute(
        select(func.coalesce(func.sum(Material.size), 0)).where(Material.user_id == user_id)
    )).scalar() or 0

    account_count = (await db.execute(
        select(func.count(PlatformAccount.id)).where(PlatformAccount.user_id == user_id)
    )).scalar() or 0

    return {
        "plan": user.plan_type,
        "plan_name": {"free": "免费版", "basic": "基础版", "pro": "专业版", "enterprise": "企业版"}.get(user.plan_type, "免费版"),
        "daily_edit": {"used": daily_used, "limit": limits["daily_edit"]},
        "monthly_edit": {"used": monthly_used, "limit": limits["monthly_edit"]},
        "accounts": {"used": account_count, "limit": limits["account_limit"]},
        "storage": {
            "used": storage_used,
            "used_gb": round(storage_used / (1024**3), 2),
            "limit": limits["storage_bytes_limit"],
            "limit_gb": round(limits["storage_bytes_limit"] / (1024**3), 1),
        },
    }
