from app.schemas.scouting_observation_schema import ScoutingObservation_schema, ScoutingObservationRead
from app.crud import crud_scouting_observation
from app.db.session import get_db
from app.services.cache_service import cache
from app.routers.deps import get_current_user
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

scouting_observation_router = APIRouter(prefix="/scouting_observations", tags=["scouting_observations"])


@scouting_observation_router.get("/", response_model=list[ScoutingObservationRead])
def get_scouting_observations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return only the observations created by the currently logged-in user."""
    return crud_scouting_observation.get_scouting_observations(
        db, skip=skip, limit=limit, scout_id=current_user.user_id
    )


@scouting_observation_router.patch("/reassign", response_model=dict)
def reassign_observations(
    to_username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reassign ALL existing observations to a target user by username.
    Requires SYSTEM_ADMIN or TEAM_ADMIN role."""
    if current_user.role not in ("SYSTEM_ADMIN", "TEAM_ADMIN"):
        raise HTTPException(status_code=403, detail="Admin role required")
    from app.crud import crud_user
    target = crud_user.get_user_by_username(db, username=to_username)
    if not target:
        raise HTTPException(status_code=404, detail=f"User '{to_username}' not found")
    updated = crud_scouting_observation.reassign_all_observations(db, to_user_id=target.user_id)
    return {"updated": updated, "assigned_to": to_username}


@scouting_observation_router.get("/{scouting_observation_id}", response_model=ScoutingObservationRead)
def get_scouting_observation(scouting_observation_id: int, db: Session = Depends(get_db)):
    scouting_observation_obj = crud_scouting_observation.get_scouting_observation(scouting_observation_id, db)
    if scouting_observation_obj is None:
        raise HTTPException(status_code=404, detail="Scouting Observation not found")
    return scouting_observation_obj


@scouting_observation_router.post("/", response_model=ScoutingObservation_schema, status_code=201)
def create_scouting_observation(scouting_observation: ScoutingObservation_schema, db: Session = Depends(get_db)):
    obs_obj = crud_scouting_observation.create_scouting_observation(scouting_observation, db)
    if obs_obj.team_id:
        cache.invalidate(cache.team_key(obs_obj.team_id))
    cache.invalidate_prefix("rankings:")
    return obs_obj


@scouting_observation_router.delete("/{scouting_observation_id}", status_code=204)
def delete_scouting_observation(scouting_observation_id: int, db: Session = Depends(get_db)):
    scouting_observation_obj = crud_scouting_observation.get_scouting_observation(scouting_observation_id, db)
    if scouting_observation_obj is None:
        raise HTTPException(status_code=404, detail="Scouting Observation not found")
    crud_scouting_observation.delete_scouting_observation(scouting_observation_id, db)
    return None