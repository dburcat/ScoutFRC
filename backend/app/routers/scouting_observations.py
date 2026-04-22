from models import scouting_observation
from db.session import get_session
from fastapi import APIRouter

scouting_observation_router = APIRouter(prefix="/scouting_observations", tags=["scouting_observations"])

@scouting_observation_router.get("/")
def get_scouting_observations():
    with get_session() as session:
        scouting_observations = session.query(scouting_observation.ScoutingObservation).all()
        return scouting_observations