from app.schemas.event_schema import Event_schema, EventSummary_schema
from app.schemas.match_schema import Match_schema
from app.schemas.team_schema import Team_schema
from app.crud import crud_event, crud_match, crud_team
from app.db.session import get_db
from app.services.cache_service import cache, TTL_EVENT, TTL_RANKINGS
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel

event_router = APIRouter(prefix="/events", tags=["events"])


@event_router.get("/", response_model=list[EventSummary_schema])
def get_events(
    year: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    db: Session = Depends(get_db),
):
    """List events — lightweight, no nested match/alliance data."""
    from app.models.event import Event
    from app.models.match import Match
    from app.models.robot_performance import RobotPerformance
    from app.models.alliance import Alliance

    events = crud_event.get_events(db, year=year, skip=skip, limit=limit)

    # Resolve counts via SQL — one query per batch, not per event
    event_ids = [e.event_id for e in events]
    if event_ids:
        match_counts = {
            row[0]: row[1]
            for row in db.query(Match.event_id, func.count(Match.match_id))
            .filter(Match.event_id.in_(event_ids))
            .group_by(Match.event_id)
            .all()
        }
        team_counts = {
            row[0]: row[1]
            for row in db.query(Match.event_id, func.count(func.distinct(RobotPerformance.team_id)))
            .join(Alliance, Alliance.match_id == Match.match_id)
            .join(RobotPerformance, RobotPerformance.alliance_id == Alliance.alliance_id)
            .filter(Match.event_id.in_(event_ids))
            .group_by(Match.event_id)
            .all()
        }
    else:
        match_counts, team_counts = {}, {}

    results = []
    for event in events:
        data = EventSummary_schema.model_validate(event).model_dump()
        data["match_count"] = match_counts.get(event.event_id, 0)
        data["team_count"] = team_counts.get(event.event_id, 0)
        results.append(EventSummary_schema.model_validate(data))

    return results


@event_router.get("/{event_id}", response_model=Event_schema)
def get_event(event_id: int, db: Session = Depends(get_db)):
    cached = cache.get(cache.event_key(event_id))
    if cached is not None:
        return cached

    event_obj = crud_event.get_event(event_id, db)
    if event_obj is None:
        raise HTTPException(status_code=404, detail="Event not found")

    cache.set(
        cache.event_key(event_id),
        Event_schema.model_validate(event_obj).model_dump(mode="json"),
        ttl=TTL_EVENT,
    )
    return event_obj


@event_router.get("/{event_id}/rankings")
def get_event_rankings(event_id: int, db: Session = Depends(get_db)):
    """Team rankings for an event, cached for 10 minutes."""
    cached = cache.get(cache.rankings_key(event_id))
    if cached is not None:
        return cached

    from app.tasks.cache_tasks import _build_event_rankings
    rankings = _build_event_rankings(db, event_id)
    cache.set(cache.rankings_key(event_id), rankings, ttl=TTL_RANKINGS)
    return rankings


@event_router.get("/{event_id}/matches", response_model=list[Match_schema])
def get_event_matches(
    event_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    db: Session = Depends(get_db),
):
    matches = crud_match.get_matches_by_event(event_id, db, skip=skip, limit=limit)
    return matches


@event_router.get("/{event_id}/teams", response_model=list[Team_schema])
def get_event_teams(
    event_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    db: Session = Depends(get_db),
):
    teams = crud_team.get_teams_by_event(event_id, db, skip=skip, limit=limit)
    return teams