# backend/app/core/scheduler.py
"""
APScheduler setup for automatic TBA syncing.

Sync strategy:
  - Active events (today falls between start_date and end_date):
      every 2 minutes  — matches post throughout the day
  - Upcoming events (start within the next 7 days):
      every 30 minutes — rosters/schedules sometimes update pre-event
  - Off-season (no active/upcoming events):
      every 6 hours    — keeps historical data fresh without hammering TBA

The scheduler runs in the same process as FastAPI using AsyncIOScheduler,
so no extra workers or queues are needed.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import SessionLocal
from app.integrations.sync_service import (
    sync_all_active_events,
    sync_season_events,
    sync_all_teams,
    sync_events_for_years,
)
from app.models.event import Event

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")

CURRENT_YEAR = date.today().year


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
    """Sync all events that are live right now."""
    logger.debug("Scheduler: syncing active events")
    with SessionLocal() as db:
        results = sync_all_active_events(db)
    synced = [r for r in results if not r.get("skipped")]
    if synced:
        logger.info("Scheduler: synced %d active event(s)", len(synced))


def _job_sync_upcoming() -> None:
    """
    Sync upcoming events — runs on a slower cadence to pick up roster
    and schedule changes before competition day.
    """
    today = date.today()
    soon = today + timedelta(days=7)
    logger.debug("Scheduler: syncing upcoming events")
    with SessionLocal() as db:
        upcoming = (
            db.query(Event)
            .filter(Event.start_date > today, Event.start_date <= soon)
            .all()
        )
        for event in upcoming:
            try:
                from app.integrations.sync_service import sync_event
                sync_event(db, event.tba_event_key)
            except Exception as exc:
                logger.warning("Upcoming sync failed for %s: %s", event.tba_event_key, exc)


def _job_bootstrap_season() -> None:
    """
    Pull the full season event list from TBA. Runs once an hour so new
    events added by FIRST mid-season appear automatically.
    """
    logger.debug("Scheduler: bootstrapping season %d", CURRENT_YEAR)
    with SessionLocal() as db:
        sync_season_events(db, CURRENT_YEAR)


def _job_startup_full_sync() -> None:
    """
    On startup, sync all historical data: all teams and events 2009-present.
    This happens once when the server starts and prepopulates the database.
    """
    logger.info("Scheduler: startup full sync — syncing all teams and events")
    with SessionLocal() as db:
        try:
            logger.info("Syncing all registered teams from TBA…")
            teams_result = sync_all_teams(db)
            logger.info("✓ Synced %d teams", teams_result["teams_synced"])
        except Exception as exc:
            logger.warning("Startup teams sync failed: %s", exc)
        
        try:
            logger.info("Syncing all events 2009-%d from TBA…", CURRENT_YEAR)
            events_result = sync_events_for_years(db, 2009, CURRENT_YEAR)
            logger.info("✓ Synced %d events", events_result["events_synced"])
        except Exception as exc:
            logger.warning("Startup events sync failed: %s", exc)


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


# ── Public API ────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    """Register all jobs and start the scheduler. Call from FastAPI startup."""
    if _scheduler.running:
        return

    # Run full startup sync immediately (once, on startup)
    _job_startup_full_sync()

    # Active-event sync — starts at 2-min cadence, dynamic reschedule adjusts it
    _scheduler.add_job(
        _job_sync_active,
        trigger=IntervalTrigger(minutes=2),
        id="sync_active",
        name="Sync active events",
        replace_existing=True,
        misfire_grace_time=30,
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
    logger.info("Scheduler started — %d jobs registered", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Graceful shutdown — call from FastAPI shutdown event."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")