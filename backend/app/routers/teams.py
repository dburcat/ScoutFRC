from models import team
from db.session import get_session
from fastapi import APIRouter

team_router = APIRouter(prefix="/teams", tags=["teams"])

@team_router.get("/")
def get_teams():
    with get_session() as session:
        teams = session.query(team.Team).all()
        return teams