from models import team
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

team_router = APIRouter(prefix="/teams", tags=["teams"])

@team_router.get("/")
def get_teams(db: Session = Depends(get_db)):
    teams = db.query(team.Team).all()
    return teams