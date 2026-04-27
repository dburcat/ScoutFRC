from sqlalchemy.orm import Session
from app.models import ScoutingObservation
from app.schemas.scouting_observation_schema import ScoutingObservation_schema

def get_scouting_observations(db: Session, skip: int = 0, limit: int = 100):
        scouting_observations = db.query(ScoutingObservation).offset(skip).limit(limit).all()
        return scouting_observations

def get_scouting_observations_count(db: Session) -> int:
        return db.query(ScoutingObservation).count()

def get_scouting_observation(scouting_observation_id: int, db: Session):
        scouting_observation_obj = db.query(ScoutingObservation).filter(ScoutingObservation.observation_id == scouting_observation_id).first()
        return scouting_observation_obj

def create_scouting_observation(scouting_observation: ScoutingObservation_schema, db: Session):
        scouting_observation_obj = ScoutingObservation(**scouting_observation.model_dump())
        db.add(scouting_observation_obj)
        db.commit()
        db.refresh(scouting_observation_obj)
        return scouting_observation_obj

def bulk_create_scouting_observations(observations: list[ScoutingObservation_schema], db: Session) -> list[ScoutingObservation]:
        created = []
        for obs in observations:
                obj = ScoutingObservation(**obs.model_dump())
                db.add(obj)
                created.append(obj)
        db.commit()
        for obj in created:
                db.refresh(obj)
        return created