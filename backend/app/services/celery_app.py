from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "zfcore",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_annotations={
        "*": {"autoretry_for": (Exception,), "retry_backoff": True, "max_retries": 3}
    }
)

celery_app.conf.beat_schedule = {
    "calculate-deep-analysis": {
        "task": "app.services.tasks.calculate_deep_analysis",
        "schedule": 10.0,
    },
    "calculate-heartbeat": {
        "task": "app.services.tasks.calculate_heartbeat",
        "schedule": 60.0,
    },
    "poll-oi-funding": {
        "task": "app.services.tasks.poll_oi_funding",
        "schedule": 60.0,  # OI + funding rate via REST every 60s
    },
    "save-mbs-snapshot": {
        "task": "app.services.tasks.save_mbs_snapshot",
        "schedule": 300.0,
    },
    "calculate-decay-prediction": {
        "task": "app.services.tasks.calculate_decay_prediction",
        "schedule": 3600.0,
    },
    "recalculate-clusters": {
        "task": "app.services.tasks.recalculate_clusters",
        "schedule": 21600.0,
    },
    "recalibrate-omega": {
        "task": "app.services.tasks.recalibrate_omega",
        "schedule": crontab(hour=0, minute=0),
    },
    "refresh-asset-registry": {
        "task": "app.services.tasks.refresh_asset_registry",
        "schedule": crontab(hour=0, minute=30),
    },
    "daily-db-backup": {
        "task": "app.services.tasks.backup_database",
        "schedule": crontab(hour=2, minute=0),
    },
    "check-demo-liquidations": {
        "task": "app.services.tasks.check_demo_liquidations",
        "schedule": 10.0,
    },
}

celery_app.autodiscover_tasks(["app.services"])
