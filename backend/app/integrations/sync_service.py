# backend/app/integrations/sync_service.py
"""
Core sync logic — shared by the scheduler (automatic) and the admin
router (manual). Extracted here so neither duplicates the other.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.crud import crud_sync_log
from app.integrations import tba_client, tba_mapper
from app.models.event import Event

logger = logging.getLogger(__name__)


def sync_event(
    db: Session,
    event_key: str,
    triggered_by: int | None = None,
) -> dict:
    """
    Fetch an event + its teams + matches from TBA and upsert into the DB.

    Returns a summary dict: { event_key, teams_synced, matches_synced }
    Raises ValueError (404) or RuntimeError (TBA error) on failure — caller
    is responsible for catching and writing the failure sync log.
    """
    tba_event   = tba_client.get_event(event_key)
    tba_teams   = tba_client.get_event_teams(event_key)
    tba_matches = tba_client.get_event_matches(event_key)

    # 304 Not Modified — nothing changed, nothing to do
    if tba_event is None or tba_teams is None or tba_matches is None:
        logger.debug("sync_event(%s): 304 Not Modified, skipping", event_key)
        return {"event_key": event_key, "teams_synced": 0, "matches_synced": 0, "skipped": True}

    if not isinstance(tba_event, dict):
        raise RuntimeError(f"Unexpected TBA event shape for {event_key}")

    event = tba_mapper.upsert_event(db, tba_event)

    team_number_to_id: dict[int, int] = {}
    for tba_team in tba_teams:
        team = tba_mapper.upsert_team(db, tba_team)
        team_number_to_id[tba_team["team_number"]] = team.team_id

    synced_matches = 0
    for tba_match in tba_matches:
        tba_mapper.upsert_match(db, tba_match, event, team_number_to_id)
        synced_matches += 1

    crud_sync_log.create_sync_log(
        db,
        sync_type="event",
        resource_id=event_key,
        status="success",
        triggered_by=triggered_by,
        records_created=len(tba_teams) + synced_matches,
        new_values={
            "event_key": event_key,
            "teams_synced": len(tba_teams),
            "matches_synced": synced_matches,
        },
    )
    db.commit()

    logger.info(
        "sync_event(%s): %d teams, %d matches",
        event_key, len(tba_teams), synced_matches,
    )
    return {
        "event_key": event_key,
        "teams_synced": len(tba_teams),
        "matches_synced": synced_matches,
        "skipped": False,
    }


def sync_all_active_events(db: Session) -> list[dict]:
    """
    Find every event in the DB whose window overlaps today and sync each one.
    Called by the scheduler on a tight interval during competition season.
    """
    today = date.today()
    active_events: list[Event] = (
        db.query(Event)
        .filter(Event.start_date <= today, Event.end_date >= today)
        .all()
    )

    results = []
    for event in active_events:
        try:
            result = sync_event(db, event.tba_event_key, triggered_by=None)
            results.append(result)
        except Exception as exc:
            logger.warning("Auto-sync failed for %s: %s", event.tba_event_key, exc)
            crud_sync_log.create_sync_log(
                db,
                sync_type="event",
                resource_id=event.tba_event_key,
                status="failed",
                triggered_by=None,
                error_message=str(exc),
            )
            db.commit()

    return results


def sync_season_events(db: Session, year: int) -> dict:
    """
    Bootstrap: fetch every event for a season from TBA and upsert them all.
    Only syncs event metadata (not teams/matches) — call sync_event per-event
    for full data. Run once at the start of a season or when deploying fresh.
    """
    logger.info("Bootstrapping season %d events from TBA", year)
    events_data = tba_client.get_events_by_year(year)

    if events_data is None:
        return {"year": year, "events_synced": 0, "skipped": True}

    count = 0
    for tba_event in events_data:
        if not isinstance(tba_event, dict):
            continue
        tba_mapper.upsert_event(db, tba_event)
        count += 1

    db.commit()
    logger.info("Bootstrapped %d events for %d", count, year)
    return {"year": year, "events_synced": count}