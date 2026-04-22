from models import scouting_observation
from schema.scouting_observation_schema import ScoutingObservation_schema
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

scouting_observation_router = APIRouter(prefix="/scouting_observations", tags=["scouting_observations"])

@scouting_observation_router.get("/", response_model=list[ScoutingObservation_schema])
def get_scouting_observations(db: Session = Depends(get_db)):
        scouting_observations = db.query(scouting_observation.ScoutingObservation).all()
        return scouting_observations

@scouting_observation_router.get("/{scouting_observation_id}", response_model=ScoutingObservation_schema)
def get_scouting_observation(scouting_observation_id: int, db: Session = Depends(get_db)):
        scouting_observation_obj = db.query(scouting_observation.ScoutingObservation).filter(scouting_observation.ScoutingObservation.observation_id == scouting_observation_id).first()
        if scouting_observation_obj is None:
                raise HTTPException(status_code=404, detail="Scouting Observation not found")
        return scouting_observation_obj