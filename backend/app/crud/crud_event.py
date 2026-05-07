from sqlalchemy.orm import Session, joinedload
from app.models import Event, Match


def get_events(db: Session, year: int | None = None, skip: int = 0, limit: int = 100):
    """List query — no relationship loading. Counts are resolved by the router via SQL."""
    q = db.query(Event)
    if year is not None:
        q = q.filter(Event.season_year == year)
    return q.offset(skip).limit(limit).all()


def get_events_count(db: Session, year: int | None = None) -> int:
    q = db.query(Event)
    if year is not None:
        q = q.filter(Event.season_year == year)
    return q.count()


def get_event(event_id: int, db: Session):
    """Single-event detail — full nested load for team_count/match_count computed fields."""
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance
    return (
        db.query(Event)
        .options(
            joinedload(Event.matches)
            .joinedload(Match.alliances)
            .joinedload(Alliance.robot_performances)
        )
        .filter(Event.event_id == event_id)
        .first()
    )