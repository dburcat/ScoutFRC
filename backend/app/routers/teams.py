from models import Team, Match, RobotPerformance
from schema.team_schema import Team_schema
from schema.match_schema import Match_schema
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

team_router = APIRouter(prefix="/teams", tags=["teams"])

@team_router.get("/", response_model=list[Team_schema])
def get_teams(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    return teams

@team_router.get("/{team_id}", response_model=Team_schema)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team_obj = db.query(Team).filter(Team.team_id == team_id).first()
    if team_obj is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team_obj

@team_router.get("/{team_id}/matches", response_model=list[Match_schema])
def get_team_matches(team_id: int, db: Session = Depends(get_db)):
    matches = db.query(Match).join(RobotPerformance).filter(RobotPerformance.team_id == team_id).all()
    return matches