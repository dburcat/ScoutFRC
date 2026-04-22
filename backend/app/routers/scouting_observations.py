from models import scouting_observation
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

scouting_observation_router = APIRouter(prefix="/scouting_observations", tags=["scouting_observations"])

@scouting_observation_router.get("/")
def get_scouting_observations(db: Session = Depends(get_db)):
        scouting_observations = db.query(scouting_observation.ScoutingObservation).all()
        return scouting_observations