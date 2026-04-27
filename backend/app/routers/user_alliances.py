from app.schemas.user_alliance_schema import UserAlliance_schema
from app.crud import crud_user_alliance
from app.db.session import get_db
from app.routers.deps import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

user_alliance_router = APIRouter(prefix="/user_alliances", tags=["user_alliances"])

@user_alliance_router.get("/", response_model=list[UserAlliance_schema])
def get_user_alliances(db: Session = Depends(get_db)):
    alliances = crud_user_alliance.get_user_alliances(db)
    return alliances

@user_alliance_router.get("/my-alliances", response_model=list[UserAlliance_schema])
def get_my_alliances(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alliances = crud_user_alliance.get_user_alliances_by_user(current_user.user_id, db)
    return alliances

@user_alliance_router.get("/{alliance_id}", response_model=UserAlliance_schema)
def get_user_alliance(alliance_id: int, db: Session = Depends(get_db)):
    alliance_obj = crud_user_alliance.get_user_alliance(alliance_id, db)
    if alliance_obj is None:
        raise HTTPException(status_code=404, detail="Alliance not found")
    return alliance_obj

@user_alliance_router.post("/", response_model=UserAlliance_schema, status_code=201)
def create_user_alliance(
    alliance: UserAlliance_schema,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only scouts and admins can create alliances
    if current_user.role not in ["SCOUT", "COACH", "TEAM_ADMIN", "SYSTEM_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized to create alliances")
    
    alliance_obj = crud_user_alliance.create_user_alliance(alliance, current_user.user_id, db)
    return alliance_obj

@user_alliance_router.delete("/{alliance_id}", status_code=204)
def delete_user_alliance(
    alliance_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alliance_obj = crud_user_alliance.get_user_alliance(alliance_id, db)
    if alliance_obj is None:
        raise HTTPException(status_code=404, detail="Alliance not found")
    
    # Only the owner or admin can delete
    if alliance_obj.user_id != current_user.user_id and current_user.role != "SYSTEM_ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to delete this alliance")
    
    crud_user_alliance.delete_user_alliance(alliance_id, db)
    return None
