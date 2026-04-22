from models import match
from schema.match_schema import Match_schema
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

match_router = APIRouter(prefix="/matches", tags=["matches"])

@match_router.get("/", response_model=list[Match_schema])
def get_matches(db: Session = Depends(get_db)):
        matches = db.query(match.Match).all()
        return matches

@match_router.get("/{match_id}", response_model=Match_schema)
def get_match(match_id: int, db: Session = Depends(get_db)):
        match_obj = db.query(match.Match).filter(match.Match.match_id == match_id).first()
        if match_obj is None:
                raise HTTPException(status_code=404, detail="Match not found")
        return match_obj