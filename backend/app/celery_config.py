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
    "default":   {"exchange": "default",   "routing_key": "default"},
    "video":     {"exchange": "video",     "routing_key": "video"},
    "analytics": {"exchange": "analytics", "routing_key": "analytics"},
    "sync":      {"exchange": "sync",      "routing_key": "sync"},
    "reports":   {"exchange": "reports",   "routing_key": "reports"},
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
    # TBA incremental sync for active events (every 2 minutes)
    "sync-tba-active": {
        "task": "tba_tasks.sync_tba_data",
        "schedule": int(os.getenv("TBA_ACTIVE_SYNC_INTERVAL_S", "120")),
        "options": {"queue": "sync"},
    },
    # TBA upcoming events sync (every 30 minutes)
    "sync-tba-upcoming": {
        "task": "tba_tasks.sync_upcoming_events",
        "schedule": int(os.getenv("TBA_UPCOMING_SYNC_INTERVAL_S", "1800")),
        "options": {"queue": "sync"},
    },
    # Season bootstrap — picks up new events added mid-season (every hour)
    "bootstrap-season": {
        "task": "tba_tasks.bootstrap_season",
        "schedule": int(os.getenv("TBA_BOOTSTRAP_INTERVAL_S", "3600")),
        "options": {"queue": "sync"},
    },
    # CV pipeline poller — checks for matches with video_url pending processing (every 2 min)
    "queue-pending-videos": {
        "task": "auto_video_tasks.queue_pending_video_matches",
        "schedule": int(os.getenv("VIDEO_POLL_INTERVAL_S", "120")),
        "options": {"queue": "default"},
    },
    # Prediction cache refresh for active/upcoming events (every 10 minutes)
    "refresh-predictions": {
        "task": "prediction_tasks.refresh_active_event_predictions",
        "schedule": int(os.getenv("PREDICTION_REFRESH_INTERVAL_S", "600")),
        "options": {"queue": "analytics"},
    },
    # Nightly model retrain to incorporate new match data (every 24 hours)
    "retrain-model": {
        "task": "prediction_tasks.scheduled_model_retrain",
        "schedule": int(os.getenv("MODEL_RETRAIN_INTERVAL_S", "86400")),
        "options": {"queue": "analytics"},
    },
    # NOTE: startup_full_sync is intentionally NOT here — it's a one-shot task
    # triggered manually via the admin endpoint when you need a full historical sync.
}