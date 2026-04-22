from sqlalchemy.orm import Session
from models import ScoutingObservation

def get_scouting_observations(db: Session):
        scouting_observations = db.query(ScoutingObservation).all()
        return scouting_observations

def get_scouting_observation(scouting_observation_id: int, db: Session):
        scouting_observation_obj = db.query(ScoutingObservation).filter(ScoutingObservation.observation_id == scouting_observation_id).first()
        return scouting_observation_obj