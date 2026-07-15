"""
Celery tasks for async video processing.
"""
from app.celery_app import celery_app
from app.services.edit_engine import EditEngine


@celery_app.task(bind=True, name="process_edit_task")
def process_edit_task(self, task_id: str, material_paths: list[str], params: dict):
    """Process a video editing task asynchronously."""
    from app.database import async_session
    from app.models import EditTask
    from sqlalchemy import select
    import asyncio

    async def update_task():
        async with async_session() as db:
            result = await db.execute(select(EditTask).where(EditTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return
            task.status = "processing"
            task.progress = 0
            await db.commit()

    asyncio.run(update_task())

    def on_progress(percent):
        async def _update():
            async with async_session() as db:
                result = await db.execute(select(EditTask).where(EditTask.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.progress = int(percent)
                    await db.commit()
        asyncio.run(_update())

    try:
        engine = EditEngine()
        outputs = engine.run_edit_task(
            task_id=task_id,
            material_paths=material_paths,
            params=params,
            progress_callback=on_progress,
        )

        async def mark_done():
            async with async_session() as db:
                result = await db.execute(select(EditTask).where(EditTask.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.status = "done"
                    task.progress = 100
                    task.output_urls = outputs
                    from datetime import datetime
                    task.completed_at = datetime.utcnow()
                    await db.commit()

        asyncio.run(mark_done())
        return {"status": "done", "output_count": len(outputs)}

    except Exception as e:
        async def mark_failed():
            async with async_session() as db:
                result = await db.execute(select(EditTask).where(EditTask.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    await db.commit()

        asyncio.run(mark_failed())
        raise


@celery_app.task(name="check_scheduled_publishes")
def check_scheduled_publishes():
    """Periodic task: check for due scheduled publish tasks and execute them."""
    import asyncio
    from datetime import datetime

    async def _check():
        from app.database import async_session
        from app.models import PublishTask, PlatformAccount
        from app.services.publisher import Publisher
        from sqlalchemy import select

        async with async_session() as db:
            now = datetime.utcnow()
            result = await db.execute(
                select(PublishTask).where(
                    PublishTask.schedule_type == "timed",
                    PublishTask.status == "pending",
                    PublishTask.schedule_time <= now,
                ).limit(10)
            )
            due_tasks = result.scalars().all()

            publisher = Publisher()
            for task in due_tasks:
                task.status = "publishing"
                await db.commit()

                # Get account
                acc_result = await db.execute(
                    select(PlatformAccount).where(PlatformAccount.id == task.platform_account_id)
                )
                account = acc_result.scalar_one_or_none()
                if not account:
                    task.status = "failed"
                    task.publish_result = {"error": "Account not found"}
                    await db.commit()
                    continue

                try:
                    result = await publisher.publish(
                        platform=account.platform,
                        account_id=str(account.id),
                        account=account,
                        video_path=task.video_url,
                        title=task.title,
                    )
                    task.status = "published" if result.get("status") == "published" else "failed"
                    task.publish_result = result
                except Exception as e:
                    task.status = "failed"
                    task.publish_result = {"error": str(e)}
                await db.commit()

    asyncio.run(_check())
    return {"checked": "ok"}


@celery_app.task(name="refresh_video_metrics")
def refresh_video_metrics():
    """Periodic task: refresh video metrics for published tasks."""
    import asyncio

    async def _refresh():
        from app.database import async_session
        from app.models import PublishTask, PlatformAccount
        from app.services.publisher import Publisher
        from sqlalchemy import select
        from datetime import datetime, timedelta

        async with async_session() as db:
            # Refresh metrics for videos published in the last 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)
            result = await db.execute(
                select(PublishTask).where(
                    PublishTask.status == "published",
                    PublishTask.created_at >= cutoff,
                )
            )
            recent_tasks = result.scalars().all()

            publisher = Publisher()
            for task in recent_tasks:
                if not task.publish_result:
                    continue
                platform_id = task.publish_result.get("platform_id")
                if not platform_id:
                    continue

                try:
                    acc_result = await db.execute(
                        select(PlatformAccount).where(PlatformAccount.id == task.platform_account_id)
                    )
                    account = acc_result.scalar_one_or_none()
                    if account:
                        metrics = await publisher.get_video_metrics(
                            platform=account.platform,
                            access_token=account.auth_token or "",
                            video_id=platform_id,
                        )
                        if metrics:
                            task.metrics = metrics
                            await db.commit()
                except Exception:
                    pass  # skip individual failures

    asyncio.run(_refresh())
    return {"refreshed": "ok"}
