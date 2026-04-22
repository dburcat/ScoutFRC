from models import Event
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

event_router = APIRouter(prefix="/events", tags=["events"])

@event_router.get("/")
def get_events(db: Session = Depends(get_db)):
        events = db.query(Event).all()
        return events