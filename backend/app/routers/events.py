from app.schemas.event_schema import Event_schema
from app.schemas.match_schema import Match_schema
from app.schemas.team_schema import Team_schema
from app.crud import crud_event, crud_match, crud_team
from app.db.session import get_db
from app.services.cache_service import cache, TTL_EVENT, TTL_RANKINGS
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

class PaginationMeta(BaseModel):
    skip: int
    limit: int
    total: int

class EventList(BaseModel):
    data: list[Event_schema]
    meta: PaginationMeta

event_router = APIRouter(prefix="/events", tags=["events"])

@event_router.get("/", response_model=list[Event_schema])
def get_events(
    year: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    db: Session = Depends(get_db)
):
        events = crud_event.get_events(db, year=year, skip=skip, limit=limit)
        return events

@event_router.get("/{event_id}", response_model=Event_schema)
def get_event(event_id: int, db: Session = Depends(get_db)):
        # Cache-aside: check cache first
        cached = cache.get(cache.event_key(event_id))
        if cached is not None:
            return cached

        event_obj = crud_event.get_event(event_id, db)
        if event_obj is None:
                raise HTTPException(status_code=404, detail="Event not found")

        # Serialize and cache
        from app.schemas.event_schema import Event_schema as EventSchema
        cache.set(cache.event_key(event_id), EventSchema.model_validate(event_obj).model_dump(mode="json"), ttl=TTL_EVENT)
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
    db: Session = Depends(get_db)
):
        matches = crud_match.get_matches_by_event(event_id, db, skip=skip, limit=limit)
        return matches
    
@event_router.get("/{event_id}/teams", response_model=list[Team_schema])
def get_event_teams(
    event_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    db: Session = Depends(get_db)
):
        teams = crud_team.get_teams_by_event(event_id, db, skip=skip, limit=limit)
        return teams