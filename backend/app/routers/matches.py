from models import match
from db.session import get_session
from fastapi import APIRouter

match_router = APIRouter(prefix="/matches", tags=["matches"])

@match_router.get("/")
def get_matches():
    with get_session() as session:
        matches = session.query(match.Match).all()
        return matches