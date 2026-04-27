from app.schemas.match_schema import Match_schema
from app.crud import crud_match
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

match_router = APIRouter(prefix="/matches", tags=["matches"])

@match_router.get("/", response_model=list[Match_schema])
def get_matches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
        matches = crud_match.get_matches(db, skip=skip, limit=limit)
        return matches

@match_router.get("/{match_id}", response_model=Match_schema)
def get_match(match_id: int, db: Session = Depends(get_db)):
        match_obj = crud_match.get_match(match_id, db)
        if match_obj is None:
                raise HTTPException(status_code=404, detail="Match not found")
        return match_obj

@match_router.get("/event/{event_id}", response_model=list[Match_schema])
def get_matches_by_event(
    event_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
        matches = crud_match.get_matches_by_event(event_id, db, skip=skip, limit=limit)
        return matches

@match_router.post("/", response_model=Match_schema, status_code=201)
def create_match(match: Match_schema, db: Session = Depends(get_db)):
        match_obj = crud_match.create_match(match, db)
        return match_obj

@match_router.patch("/{match_id}", response_model=Match_schema)
def update_match(match_id: int, match: Match_schema, db: Session = Depends(get_db)):
        match_obj = crud_match.update_match(match_id, match, db)
        if match_obj is None:
                raise HTTPException(status_code=404, detail="Match not found")
        return match_obj