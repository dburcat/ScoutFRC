from sqlalchemy.orm import Session
from models import Match

def get_matches(db: Session):
        matches = db.query(Match).all()
        return matches

def get_match(match_id: int, db: Session):
        match_obj = db.query(Match).filter(Match.match_id == match_id).first()
        return match_obj

def get_matches_by_event(event_id: int, db: Session):
        matches = db.query(Match).filter(Match.event_id == event_id).all()
        return matches