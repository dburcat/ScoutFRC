from models import Event, Match, Team, RobotPerformance
from schema.event_schema import Event_schema
from schema.match_schema import Match_schema
from schema.team_schema import Team_schema
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

event_router = APIRouter(prefix="/events", tags=["events"])

@event_router.get("/", response_model=list[Event_schema])
def get_events(db: Session = Depends(get_db)):
        events = db.query(Event).all()
        return events

@event_router.get("/{event_id}", response_model=Event_schema)
def get_event(event_id: int, db: Session = Depends(get_db)):
        event_obj = db.query(Event).filter(Event.event_id == event_id).first()
        if event_obj is None:
                raise HTTPException(status_code=404, detail="Event not found")
        return event_obj

@event_router.get("/{event_id}/matches", response_model=list[Match_schema])
def get_event_matches(event_id: int, db: Session = Depends(get_db)):
        matches = db.query(Match).filter(Match.event_id == event_id).all()
        return matches

@event_router.get("/{event_id}/teams", response_model=list[Team_schema])
def get_event_teams(event_id: int, db: Session = Depends(get_db)):
        teams = db.query(Team).join(RobotPerformance).join(Match).filter(Match.event_id == id).distinct().all()
        return teams

