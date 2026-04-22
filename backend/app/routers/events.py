from models import Event
from db.session import get_session
from fastapi import APIRouter

event_router = APIRouter(prefix="/events", tags=["events"])

@event_router.get("/")
def get_events():
    with get_session() as session:
        events = session.query(Event).all()
        return events