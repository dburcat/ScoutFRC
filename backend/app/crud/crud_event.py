from sqlalchemy.orm import Session
from app.models import Event

def get_events(db: Session):
        events = db.query(Event).all()
        return events

def get_event(event_id: int, db: Session):
        event_obj = db.query(Event).filter(Event.event_id == event_id).first()
        return event_obj


