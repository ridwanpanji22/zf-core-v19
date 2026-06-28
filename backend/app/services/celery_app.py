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
    broker_connection_retry_on_startup=True
)

celery_app.conf.beat_schedule = {
    "calculate-deep-analysis": {
        "task": "app.services.tasks.calculate_deep_analysis",
        "schedule": 10.0, # every 10 seconds
    },
    "calculate-heartbeat": {
        "task": "app.services.tasks.calculate_heartbeat",
        "schedule": 60.0, # every 60 seconds
    },
    "save-mbs-snapshot": {
        "task": "app.services.tasks.save_mbs_snapshot",
        "schedule": 300.0, # every 5 minutes
    },
    "calculate-decay-prediction": {
        "task": "app.services.tasks.calculate_decay_prediction",
        "schedule": 3600.0, # every 1 hour
    },
    "recalculate-clusters": {
        "task": "app.services.tasks.recalculate_clusters",
        "schedule": 21600.0, # every 6 hours
    },
    "recalibrate-omega": {
        "task": "app.services.tasks.recalibrate_omega",
        "schedule": crontab(hour=0, minute=0), # daily at 00:00 UTC
    },
    "refresh-asset-registry": {
        "task": "app.services.tasks.refresh_asset_registry",
        "schedule": crontab(hour=0, minute=30), # daily at 00:30 UTC
    },
    "daily-db-backup": {
        "task": "app.services.tasks.backup_database",
        "schedule": crontab(hour=2, minute=0), # daily at 02:00 UTC
    },
    "check-demo-liquidations": {
        "task": "app.services.tasks.check_demo_liquidations",
        "schedule": 10.0, # every 10 seconds
    },
}

celery_app.autodiscover_tasks(["app.services"])
