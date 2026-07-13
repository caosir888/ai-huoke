"""
Publish scheduler: handles timed and recurring video publishing.
"""
import asyncio
from datetime import datetime, timedelta
import threading
import time

from app.services.publisher import Publisher

publisher = Publisher()


class PublishScheduler:
    """Simple in-process scheduler for timed publish tasks."""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                asyncio.run(self._check_and_publish())
            except Exception as e:
                print(f"Scheduler error: {e}")
            time.sleep(self.check_interval)

    async def _check_and_publish(self):
        """Check for due publish tasks and execute them."""
        from app.database import async_session
        from app.models import PublishTask, PlatformAccount
        from sqlalchemy import select

        now = datetime.utcnow()
        async with async_session() as db:
            # Find pending timed tasks that are due
            result = await db.execute(
                select(PublishTask)
                .where(
                    PublishTask.status == "pending",
                    PublishTask.schedule_type == "timed",
                    PublishTask.schedule_time <= now,
                )
                .limit(10)
            )
            tasks = result.scalars().all()

            for task in tasks:
                task.status = "publishing"
                await db.commit()

                # Resolve platform account
                acc_result = await db.execute(
                    select(PlatformAccount).where(PlatformAccount.id == task.platform_account_id)
                )
                account = acc_result.scalar_one_or_none()
                if not account:
                    task.status = "failed"
                    task.publish_result = {"error": "account not found"}
                    await db.commit()
                    continue

                # Execute publish
                try:
                    result = await publisher.publish(
                        platform=account.platform,
                        account_id=str(account.id),
                        access_token=account.auth_token or "",
                        video_path=task.video_url,
                        title=task.title,
                    )
                    task.status = "published" if result["status"] == "published" else "queued"
                    task.publish_result = result
                except Exception as e:
                    task.status = "failed"
                    task.publish_result = {"error": str(e)}

                await db.commit()
