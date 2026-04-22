from sqlalchemy.orm import Session
from app.models import ScoutingObservation
from app.schema.scouting_observation_schema import ScoutingObservation_schema

def get_scouting_observations(db: Session):
        scouting_observations = db.query(ScoutingObservation).all()
        return scouting_observations

def get_scouting_observation(scouting_observation_id: int, db: Session):
        scouting_observation_obj = db.query(ScoutingObservation).filter(ScoutingObservation.observation_id == scouting_observation_id).first()
        return scouting_observation_obj

def create_scouting_observation(scouting_observation: ScoutingObservation_schema, db: Session):
        scouting_observation_obj = ScoutingObservation(**scouting_observation.model_dump())
        db.add(scouting_observation_obj)
        db.commit()
        db.refresh(scouting_observation_obj)
        return scouting_observation_obj