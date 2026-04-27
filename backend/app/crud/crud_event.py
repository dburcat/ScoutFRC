from sqlalchemy.orm import Session, joinedload
from app.models import Event, Match


def get_events(db: Session, year: int | None = None, skip: int = 0, limit: int = 100):
    q = db.query(Event).options(
        joinedload(Event.matches).joinedload(Match.alliances)
    )
    if year is not None:
        q = q.filter(Event.season_year == year)
    return q.offset(skip).limit(limit).all()


def get_events_count(db: Session, year: int | None = None) -> int:
    q = db.query(Event)
    if year is not None:
        q = q.filter(Event.season_year == year)
    return q.count()


def get_event(event_id: int, db: Session):
    return (
        db.query(Event)
        .options(joinedload(Event.matches).joinedload(Match.alliances))
        .filter(Event.event_id == event_id)
        .first()
    )