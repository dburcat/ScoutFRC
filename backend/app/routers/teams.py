from app.schemas.team_schema import Team_schema
from app.schemas.match_schema import Match_schema
from app.crud import crud_team
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

team_router = APIRouter(prefix="/teams", tags=["teams"])

@team_router.get("/", response_model=list[Team_schema])
def get_teams(
    team_number: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    teams = crud_team.get_teams(db, team_number=team_number, skip=skip, limit=limit)
    return teams

@team_router.get("/{team_id}", response_model=Team_schema)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team_obj = crud_team.get_team(team_id, db)
    if team_obj is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team_obj

@team_router.get("/{team_id}/matches", response_model=list[Match_schema])
def get_team_matches(team_id: int, db: Session = Depends(get_db)):
    matches = crud_team.get_team_matches(team_id, db)
    return matches