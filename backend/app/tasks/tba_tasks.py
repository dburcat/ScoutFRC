"""
tba_tasks.py
============
Phase 2 Tier 5 — Blue Alliance Continuous Sync

Tasks
-----
sync_tba_data
    Celery Beat periodic task (default every 5 min).
    Incrementally syncs active/upcoming events and their match results.
    Records every run in SyncLog. Sends failure alert after 3 consecutive failures.

Full sync functions are separated from the Celery task so they can be
called directly from admin endpoints without dispatching to a worker.
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.integrations.sync_service import sync_event
from app.services.cache_service import cache

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
# How many days before/after today to consider an event "active"
ACTIVE_WINDOW_DAYS_BEFORE: int = int(os.getenv("SYNC_ACTIVE_WINDOW_BEFORE", "1"))
ACTIVE_WINDOW_DAYS_AFTER: int = int(os.getenv("SYNC_ACTIVE_WINDOW_AFTER", "7"))

# Number of consecutive failures before sending an alert
CONSECUTIVE_FAILURE_THRESHOLD: int = int(os.getenv("SYNC_FAILURE_THRESHOLD", "3"))

# Redis key for tracking consecutive failure count
_FAILURE_COUNT_KEY = "tba_sync:consecutive_failures"


# ── Failure tracking ──────────────────────────────────────────────────────────

def _get_failure_count() -> int:
    try:
        val = cache.get(_FAILURE_COUNT_KEY)
        return int(val) if val is not None else 0
    except Exception:
        return 0


def _increment_failure_count() -> int:
    try:
        count = _get_failure_count() + 1
        cache.set(_FAILURE_COUNT_KEY, count, ttl=86400)  # 24h TTL
        return count
    except Exception:
        return 0


def _reset_failure_count() -> None:
    try:
        cache.invalidate(_FAILURE_COUNT_KEY)
    except Exception:
        pass


def _send_failure_alert(consecutive: int, error: str) -> None:
    """Log a prominent failure alert. Extend to webhook/email as needed."""
    logger.critical(
        "TBA SYNC FAILURE ALERT: %d consecutive failures. Last error: %s",
        consecutive,
        error,
    )
    # Optional: send to a webhook URL if configured
    webhook_url = os.getenv("SYNC_ALERT_WEBHOOK_URL")
    if webhook_url:
        try:
            import httpx
            httpx.post(
                webhook_url,
                json={
                    "text": f"⚠️ TBA sync has failed {consecutive} times consecutively.\nLast error: {error}"
                },
                timeout=5,
            )
        except Exception as exc:
            logger.warning("Failed to send alert webhook: %s", exc)


# ── Core sync logic ───────────────────────────────────────────────────────────

def _get_active_event_keys(db) -> list[str]:
    """Return TBA event keys for events active within the sync window."""
    from app.models.event import Event

    today = date.today()
    window_start = today - timedelta(days=ACTIVE_WINDOW_DAYS_BEFORE)
    window_end = today + timedelta(days=ACTIVE_WINDOW_DAYS_AFTER)

    events = (
        db.query(Event)
        .filter(
            Event.start_date <= window_end,
            Event.end_date >= window_start,
        )
        .all()
    )
    return [e.tba_event_key for e in events if e.tba_event_key]


def run_incremental_sync(db) -> dict:
    """
    Core sync logic — callable from both the Celery task and admin endpoints.

    Returns a summary dict suitable for SyncLog persistence.
    """
    event_keys = _get_active_event_keys(db)

    if not event_keys:
        logger.info("sync_tba_data: no active events in window, skipping")
        return {
            "events_attempted": 0,
            "events_synced": 0,
            "events_skipped": 0,
            "events_failed": 0,
            "status": "no_active_events",
        }

    logger.info("sync_tba_data: syncing %d active events: %s", len(event_keys), event_keys)

    synced = skipped = failed = 0
    for key in event_keys:
        try:
            result = sync_event(db, key)
            if result.get("skipped"):
                skipped += 1
            else:
                synced += 1
        except Exception as exc:
            failed += 1
            logger.error("sync_tba_data: failed to sync %s: %s", key, exc)

    return {
        "events_attempted": len(event_keys),
        "events_synced": synced,
        "events_skipped": skipped,
        "events_failed": failed,
        "status": "complete" if failed == 0 else "partial",
    }


def _write_sync_log(db, result: dict, error_message: str | None = None) -> None:
    """Persist a SyncLog row for this sync run."""
    from app.models.sync_log import SyncLog

    status = "success" if not error_message else "failure"
    db.add(SyncLog(
        sync_type="tba_periodic",
        resource_id="active_events",
        status=status,
        records_created=result.get("events_synced", 0),
        records_updated=result.get("events_skipped", 0),
        error_message=error_message,
        new_values=result,
    ))
    db.commit()


# ── Celery task ───────────────────────────────────────────────────────────────

@celery_app.task(
    name="tba_tasks.sync_tba_data",
    queue="sync",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def sync_tba_data() -> dict:
    """
    Periodic Celery Beat task: incrementally sync TBA data for active events.
    Tracks consecutive failures and sends an alert after the threshold is reached.
    """
    logger.info("sync_tba_data: starting periodic sync")

    try:
        with SessionLocal() as db:
            result = run_incremental_sync(db)
            _write_sync_log(db, result)

        _reset_failure_count()
        logger.info("sync_tba_data: complete %s", result)
        return result

    except Exception as exc:
        error_msg = str(exc)
        logger.error("sync_tba_data: task failed: %s", error_msg)

        # Track consecutive failures
        consecutive = _increment_failure_count()
        if consecutive >= CONSECUTIVE_FAILURE_THRESHOLD:
            _send_failure_alert(consecutive, error_msg)

        # Write failure log
        try:
            with SessionLocal() as db:
                _write_sync_log(db, {}, error_message=error_msg)
        except Exception:
            pass

        raise