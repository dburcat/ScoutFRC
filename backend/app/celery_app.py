"""
Celery application factory for ScouterFRC.

Broker  : Redis  (REDIS_URL env var, default redis://redis:6379/0)
Backend : Redis  (same URL, DB 1)
Queues  : default | video | analytics | sync | reports

Configuration is loaded from app.celery_config module.
"""

from celery import Celery
from app import celery_config

celery_app = Celery(
    "scouterfrc",
    broker=celery_config.REDIS_URL,
    backend=celery_config.REDIS_RESULT_URL,
    include=[
        "app.tasks.sample",   # sample / health-check task
        "app.tasks.video_tasks",  # video CV pipeline tasks
        "app.tasks.analytics_tasks",  # robot performance analytics
        "app.tasks.cache_tasks",  # cache refresh and warmup
        "app.tasks.tba_tasks",  # TBA continuous sync
        "app.tasks.report_tasks",  # report generation
        "app.tasks.prediction_tasks",  # ML prediction model training & batch scoring
        "app.tasks.auto_video_tasks",  # automatic video download + CV processing
    ],
)

celery_app.config_from_object(celery_config)