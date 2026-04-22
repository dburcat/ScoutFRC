from models import team
from schema.team_schema import Team_schema
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

team_router = APIRouter(prefix="/teams", tags=["teams"])

@team_router.get("/", response_model=list[Team_schema])
def get_teams(db: Session = Depends(get_db)):
    teams = db.query(team.Team).all()
    return teams

@team_router.get("/{team_id}", response_model=Team_schema)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team_obj = db.query(team.Team).filter(team.Team.team_id == team_id).first()
    if team_obj is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team_obj