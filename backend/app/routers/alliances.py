from models import alliance
from db.session import get_session
from fastapi import APIRouter

alliance_router = APIRouter(prefix="/alliances", tags=["alliances"])

@alliance_router.get("/")
def get_alliances():
    with get_session() as session:
        alliances = session.query(alliance.Alliance).all()
        return alliances