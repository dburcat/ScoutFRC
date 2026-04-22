from sqlalchemy.orm import Session
from models import Match
from schema.match_schema import Match_schema

def get_matches(db: Session):
        matches = db.query(Match).all()
        return matches

def get_match(match_id: int, db: Session):
        match_obj = db.query(Match).filter(Match.match_id == match_id).first()
        return match_obj

def get_matches_by_event(event_id: int, db: Session):
        matches = db.query(Match).filter(Match.event_id == event_id).all()
        return matches

def create_match(match: Match_schema, db: Session):
        match_obj = Match(**match.model_dump())
        db.add(match_obj)
        db.commit()
        db.refresh(match_obj)
        return match_obj