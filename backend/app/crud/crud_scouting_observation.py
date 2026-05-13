from sqlalchemy.orm import Session, joinedload
from app.models import ScoutingObservation, Match
from app.schemas.scouting_observation_schema import ScoutingObservation_schema


def get_scouting_observations(db: Session, skip: int = 0, limit: int = 100, scout_id: int | None = None):
    q = db.query(ScoutingObservation).options(
        joinedload(ScoutingObservation.match).joinedload(Match.event),
        joinedload(ScoutingObservation.team),
    )
    if scout_id is not None:
        q = q.filter(ScoutingObservation.scout_id == scout_id)
    return q.order_by(ScoutingObservation.submitted_at.desc()).offset(skip).limit(limit).all()


def get_scouting_observations_count(db: Session) -> int:
    return db.query(ScoutingObservation).count()


def get_scouting_observation(scouting_observation_id: int, db: Session):
    return (
        db.query(ScoutingObservation)
        .options(
            joinedload(ScoutingObservation.match).joinedload(Match.event),
            joinedload(ScoutingObservation.team),
        )
        .filter(ScoutingObservation.observation_id == scouting_observation_id)
        .first()
    )


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


def reassign_all_observations(db: Session, to_user_id: int) -> int:
    """Bulk-update every observation to a new scout_id. Returns number of rows updated."""
    updated = db.query(ScoutingObservation).update({"scout_id": to_user_id}, synchronize_session=False)
    db.commit()
    return updated


def delete_scouting_observation(scouting_observation_id: int, db: Session):
    scouting_observation_obj = (
        db.query(ScoutingObservation)
        .options(
            joinedload(ScoutingObservation.match).joinedload(Match.event),
            joinedload(ScoutingObservation.team),
        )
        .filter(ScoutingObservation.observation_id == scouting_observation_id)
        .first()
    )
    if scouting_observation_obj:
        db.delete(scouting_observation_obj)
        db.commit()
    return scouting_observation_obj