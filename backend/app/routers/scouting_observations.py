from schema.scouting_observation_schema import ScoutingObservation_schema
from crud import crud_scouting_observation
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

scouting_observation_router = APIRouter(prefix="/scouting_observations", tags=["scouting_observations"])

@scouting_observation_router.get("/", response_model=list[ScoutingObservation_schema])
def get_scouting_observations(db: Session = Depends(get_db)):
        scouting_observations = crud_scouting_observation.get_scouting_observations(db)
        return scouting_observations

@scouting_observation_router.get("/{scouting_observation_id}", response_model=ScoutingObservation_schema)
def get_scouting_observation(scouting_observation_id: int, db: Session = Depends(get_db)):
        scouting_observation_obj = crud_scouting_observation.get_scouting_observation(scouting_observation_id, db)
        if scouting_observation_obj is None:
                raise HTTPException(status_code=404, detail="Scouting Observation not found")
        return scouting_observation_obj

@scouting_observation_router.post("/", response_model=ScoutingObservation_schema, status_code=201)
def create_scouting_observation(scouting_observation: ScoutingObservation_schema, db: Session = Depends(get_db)):
        scouting_observation_obj = crud_scouting_observation.create_scouting_observation(scouting_observation, db)
        return scouting_observation_obj