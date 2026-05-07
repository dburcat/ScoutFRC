# backend/app/core/scheduler.py
"""
APScheduler setup for automatic task dispatch to Celery workers.

Architecture:
  - APScheduler runs in the FastAPI process (AsyncIOScheduler)
  - All sync/processing jobs dispatch Celery tasks to worker queues
  - Celery workers pick up and execute tasks from Redis queues
  - Sync strategy dynamically adjusts poll frequency based on event calendar

Sync strategy:
  - Active events (today falls between start_date and end_date):
      every 2 minutes  — matches post throughout the day
  - Upcoming events (start within the next 7 days):
      every 30 minutes — rosters/schedules sometimes update pre-event
  - Off-season (no active/upcoming events):
      every 6 hours    — keeps historical data fresh without hammering TBA
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import SessionLocal
from app.models.event import Event
from app.tasks.auto_video_tasks import queue_pending_video_matches

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_active_events() -> bool:
    """Return True if any event is live today."""
    today = date.today()
    with SessionLocal() as db:
        return (
            db.query(Event)
            .filter(Event.start_date <= today, Event.end_date >= today)
            .first()
        ) is not None


def _has_upcoming_events(days: int = 7) -> bool:
    """Return True if any event starts within the next N days."""
    today = date.today()
    soon = today + timedelta(days=days)
    with SessionLocal() as db:
        return (
            db.query(Event)
            .filter(Event.start_date > today, Event.start_date <= soon)
            .first()
        ) is not None


# ── Job functions ─────────────────────────────────────────────────────────────

def _job_sync_active() -> None:
    """Dispatch active event sync to Celery worker."""
    from app.tasks.tba_tasks import sync_tba_data
    logger.debug("Scheduler: dispatching sync_tba_data to Celery worker")
    try:
        result = sync_tba_data.apply_async(queue="sync")  # type: ignore[union-attr]
        logger.info("Scheduler: sync_tba_data dispatched (task_id=%s)", result.id)
    except Exception as exc:
        logger.warning("Scheduler: failed to dispatch sync_tba_data: %s", exc)


def _job_auto_video() -> None:
    """
    After each active-event sync, dispatch video processing for matches
    that now have a video_url but haven't been processed yet.
    """
    logger.debug("Scheduler: checking for pending match videos to queue")
    try:
        queued = queue_pending_video_matches()
        if queued:
            logger.info("Scheduler: queued %d match video(s) for CV processing", queued)
    except Exception as exc:
        logger.warning("Scheduler: auto-video queue failed: %s", exc)


def _job_sync_upcoming() -> None:
    """Dispatch upcoming events sync to Celery worker."""
    from app.tasks.tba_tasks import sync_upcoming_events
    logger.debug("Scheduler: dispatching sync_upcoming_events to Celery worker")
    try:
        result = sync_upcoming_events.apply_async(queue="sync")  # type: ignore[union-attr]
        logger.info("Scheduler: sync_upcoming_events dispatched (task_id=%s)", result.id)
    except Exception as exc:
        logger.warning("Scheduler: failed to dispatch sync_upcoming_events: %s", exc)


def _job_bootstrap_season() -> None:
    """Dispatch season bootstrap to Celery worker."""
    from app.tasks.tba_tasks import bootstrap_season
    logger.debug("Scheduler: dispatching bootstrap_season to Celery worker")
    try:
        result = bootstrap_season.apply_async(queue="sync")  # type: ignore[union-attr]
        logger.info("Scheduler: bootstrap_season dispatched (task_id=%s)", result.id)
    except Exception as exc:
        logger.warning("Scheduler: failed to dispatch bootstrap_season: %s", exc)


def _job_startup_full_sync() -> None:
    """Dispatch full startup sync to Celery worker."""
    from app.tasks.tba_tasks import startup_full_sync
    logger.info("Scheduler: dispatching startup_full_sync to Celery worker")
    try:
        result = startup_full_sync.apply_async(queue="sync")  # type: ignore[union-attr]
        logger.info("Scheduler: startup_full_sync dispatched (task_id=%s)", result.id)
    except Exception as exc:
        logger.warning("Scheduler: failed to dispatch startup_full_sync: %s", exc)


def _job_dynamic_reschedule() -> None:
    """
    Every minute, check whether we need the fast (2-min) or slow (30-min)
    active-event job and reschedule accordingly. This avoids hammering TBA
    between events while staying responsive during competition.
    """
    active   = _has_active_events()
    upcoming = _has_upcoming_events()

    # Active events: poll every 2 minutes
    if active:
        _reschedule("sync_active", minutes=2)
    # No active events, but some starting soon: poll every 30 minutes
    elif upcoming:
        _reschedule("sync_active", minutes=30)
    # Quiet period: poll every 6 hours
    else:
        _reschedule("sync_active", hours=6)


def _reschedule(job_id: str, **interval_kwargs: int) -> None:
    job = _scheduler.get_job(job_id)
    if job is None:
        return
    new_trigger = IntervalTrigger(**interval_kwargs)
    # Only reschedule if the interval has actually changed
    current = getattr(job.trigger, "interval", None)
    from datetime import timedelta as td
    new_td = td(**interval_kwargs)
    if current != new_td:
        job.reschedule(trigger=new_trigger)
        logger.info("Scheduler: '%s' rescheduled → %s", job_id, interval_kwargs)


# ── Dev flag ──────────────────────────────────────────────────────────────────
# Set to True when you're ready to re-enable automatic TBA syncing.
# All sync logic/jobs below are preserved; this just stops them from running.
# APScheduler-based dispatch is disabled — Celery Beat now owns all periodic
# task scheduling (see celery_config.py beat_schedule). APScheduler had
# reliability issues under uvicorn --reload and is redundant with beat.
# Set to True only if you need dynamic interval adjustment at runtime.
AUTOSYNC_ENABLED = False


# ── Public API ────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    """Register all jobs and start the scheduler. Call from FastAPI startup."""
    if not AUTOSYNC_ENABLED:
        logger.info(
            "Scheduler: AUTOSYNC_ENABLED=False — auto-sync suspended "
            "(flip to True in scheduler.py to re-enable)"
        )
        return

    if _scheduler.running:
        return

    try:
        # NOTE: Full startup sync is commented out because:
        # 1. It takes ~10 minutes to complete (syncs all 9k+ teams & 200+ events)
        # 2. Dynamic TBA syncing (sync_tba_data) keeps data fresh automatically
        # 3. Uncomment only if you need a full historical sync on server restart
        #
        # _scheduler.add_job(
        #     _job_startup_full_sync,
        #     trigger="date",
        #     run_date=None,
        #     id="startup_sync",
        #     name="Startup full sync",
        # )

        # Active-event sync — starts at 2-min cadence, dynamic reschedule adjusts it
        _scheduler.add_job(
            _job_sync_active,
            trigger=IntervalTrigger(minutes=2),
            id="sync_active",
            name="Sync active events",
            replace_existing=True,
            misfire_grace_time=30,
        )

        # Auto video processing — runs every 2 minutes, checking for new match videos
        # Only dispatches work when matches have video_url and are still pending
        _scheduler.add_job(
            _job_auto_video,
            trigger=IntervalTrigger(minutes=2),
            id="auto_video",
            name="Auto video processing",
            replace_existing=True,
            misfire_grace_time=60,
        )

        # Upcoming-event sync — every 30 minutes
        _scheduler.add_job(
            _job_sync_upcoming,
            trigger=IntervalTrigger(minutes=30),
            id="sync_upcoming",
            name="Sync upcoming events",
            replace_existing=True,
            misfire_grace_time=120,
        )

        # Season bootstrap — every hour
        _scheduler.add_job(
            _job_bootstrap_season,
            trigger=IntervalTrigger(hours=1),
            id="bootstrap_season",
            name="Bootstrap season events",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # Dynamic reschedule check — every minute
        _scheduler.add_job(
            _job_dynamic_reschedule,
            trigger=IntervalTrigger(minutes=1),
            id="dynamic_reschedule",
            name="Dynamic interval tuner",
            replace_existing=True,
        )

        _scheduler.start()
        job_count = len(_scheduler.get_jobs())
        logger.info("Scheduler started — %d jobs registered (excluding startup_full_sync)", job_count)
    except Exception as exc:
        logger.error("Scheduler startup failed: %s", exc, exc_info=True)


def stop_scheduler() -> None:
    """Graceful shutdown — call from FastAPI shutdown event."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")