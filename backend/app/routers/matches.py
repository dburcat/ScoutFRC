from schema.match_schema import Match_schema
from crud import crud_match
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

match_router = APIRouter(prefix="/matches", tags=["matches"])

@match_router.get("/", response_model=list[Match_schema])
def get_matches(db: Session = Depends(get_db)):
        matches = crud_match.get_matches(db)
        return matches

@match_router.get("/{match_id}", response_model=Match_schema)
def get_match(match_id: int, db: Session = Depends(get_db)):
        match_obj = crud_match.get_match(match_id, db)
        if match_obj is None:
                raise HTTPException(status_code=404, detail="Match not found")
        return match_obj