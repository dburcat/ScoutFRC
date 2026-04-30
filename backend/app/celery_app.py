"""
Celery application factory for ScouterFRC.

Broker  : Redis  (REDIS_URL env var, default redis://redis:6379/0)
Backend : Redis  (same URL, DB 1)
Queues  : default | video | analytics | sync | reports
"""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Use a separate Redis DB for result backend to avoid key collisions
REDIS_RESULT_URL = os.getenv("REDIS_RESULT_URL", "redis://localhost:6379/1")

celery_app = Celery(
    "scouterfrc",
    broker=REDIS_URL,
    backend=REDIS_RESULT_URL,
    include=[
        "app.tasks.sample",   # sample / health-check task
    ],
)

celery_app.conf.update(
    # ── Serialization ─────────────────────────────────────────────────────────
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # ── Timezone ──────────────────────────────────────────────────────────────
    timezone="UTC",
    enable_utc=True,
    # ── Result expiry ─────────────────────────────────────────────────────────
    result_expires=3600,        # 1 hour
    # ── Retry / reliability ───────────────────────────────────────────────────
    task_acks_late=True,        # only ack after task completes (safer)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,   # one task at a time per worker process
    # ── Queue routing ─────────────────────────────────────────────────────────
    task_default_queue="default",
    task_queues={
        "default":   {"exchange": "default",   "routing_key": "default"},
        "video":     {"exchange": "video",     "routing_key": "video"},
        "analytics": {"exchange": "analytics", "routing_key": "analytics"},
        "sync":      {"exchange": "sync",      "routing_key": "sync"},
        "reports":   {"exchange": "reports",   "routing_key": "reports"},
    },
    # ── Retry backoff defaults (tasks can override) ────────────────────────────
    task_annotations={
        "*": {
            "max_retries": 3,
            "default_retry_delay": 60,   # seconds
        }
    },
    # ── Flower / monitoring ───────────────────────────────────────────────────
    worker_send_task_events=True,
    task_send_sent_event=True,
)