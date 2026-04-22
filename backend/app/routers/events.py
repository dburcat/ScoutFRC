from models import Event
from schema.event_schema import Event_schema
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

