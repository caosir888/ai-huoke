from celery import Celery
from app.config import settings

celery_app = Celery(
    "ai_huoke",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 min max per edit task
    worker_concurrency=2,  # limit FFmpeg concurrency
    beat_schedule={
        "check-scheduled-publishes": {
            "task": "app.services.tasks.check_scheduled_publishes",
            "schedule": 30.0,  # check every 30 seconds
        },
        "refresh-video-metrics": {
            "task": "app.services.tasks.refresh_video_metrics",
            "schedule": 3600.0,  # refresh metrics every hour
        },
    },
)

celery_app.autodiscover_tasks(["app.services"])
