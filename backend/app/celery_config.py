"""
Celery configuration for ScouterFRC.

Defines queues, serialization, retry policies, and monitoring settings.
"""

import os

# ── Broker & Backend ──────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_RESULT_URL = os.getenv("REDIS_RESULT_URL", "redis://localhost:6379/1")

# ── Serialization ─────────────────────────────────────────────────────────────
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# ── Timezone ──────────────────────────────────────────────────────────────────
timezone = "UTC"
enable_utc = True

# ── Result expiry ─────────────────────────────────────────────────────────────
result_expires = 3600  # 1 hour

# ── Retry / reliability ───────────────────────────────────────────────────────
task_acks_late = True  # only ack after task completes (safer)
task_reject_on_worker_lost = True
worker_prefetch_multiplier = 1  # one task at a time per worker process

# ── Queue routing ─────────────────────────────────────────────────────────────
task_default_queue = "default"

task_queues = {
    "default": {"exchange": "default", "routing_key": "default"},
    "video": {"exchange": "video", "routing_key": "video"},
    "analytics": {"exchange": "analytics", "routing_key": "analytics"},
    "sync": {"exchange": "sync", "routing_key": "sync"},
    "reports": {"exchange": "reports", "routing_key": "reports"},
}

# ── Retry backoff defaults (tasks can override) ───────────────────────────────
task_annotations = {
    "*": {
        "max_retries": 3,
        "default_retry_delay": 60,  # seconds
    }
}

# ── Flower / monitoring ───────────────────────────────────────────────────────
worker_send_task_events = True
task_send_sent_event = True

# ── Celery Beat schedule ──────────────────────────────────────────────────────
beat_schedule = {
    # Dashboard cache refresh (every 10 minutes)
    "refresh-dashboard-cache": {
        "task": "cache_tasks.refresh_dashboard_cache",
        "schedule": int(os.getenv("CACHE_REFRESH_INTERVAL_S", "600")),
        "options": {"queue": "default"},
    },
    # NOTE: TBA sync tasks are intentionally NOT here — APScheduler in the FastAPI
    # process handles TBA syncing with dynamic intervals based on active events.
    # Having them in beat_schedule too would cause duplicate syncs hammering TBA.
    # To use dynamic scheduling, run FastAPI alongside Celery Worker and Beat.
}