from sqlalchemy.orm import Session, joinedload
from app.models import Match
from app.schemas.match_schema import Match_schema

def get_matches(db: Session, skip: int = 0, limit: int = 100):
        matches = db.query(Match).options(joinedload(Match.robot_performances)).offset(skip).limit(limit).all()
        return matches

def get_matches_count(db: Session) -> int:
        return db.query(Match).count()

def get_match(match_id: int, db: Session):
        match_obj = db.query(Match).options(joinedload(Match.robot_performances)).filter(Match.match_id == match_id).first()
        return match_obj

def get_matches_by_event(event_id: int, db: Session, skip: int = 0, limit: int = 100):
        matches = db.query(Match).options(joinedload(Match.robot_performances)).filter(Match.event_id == event_id).offset(skip).limit(limit).all()
        return matches

def get_matches_by_event_count(event_id: int, db: Session) -> int:
        return db.query(Match).filter(Match.event_id == event_id).count()

def create_match(match: Match_schema, db: Session):
        match_obj = Match(**match.model_dump())
        db.add(match_obj)
        db.commit()
        db.refresh(match_obj)
        return match_obj

def update_match(match_id: int, match: Match_schema, db: Session):
        match_obj = db.query(Match).filter(Match.match_id == match_id).first()
        if match_obj is None:
                return None
        for key, value in match.model_dump().items():
                setattr(match_obj, key, value)
        db.commit()
        db.refresh(match_obj)
        return match_obj