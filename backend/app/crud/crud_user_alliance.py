from sqlalchemy.orm import Session
from app.models import UserAlliance
from app.schemas.user_alliance_schema import UserAlliance_schema

def get_user_alliances(db: Session):
    alliances = db.query(UserAlliance).all()
    return alliances

def get_user_alliance(alliance_id: int, db: Session):
    alliance_obj = db.query(UserAlliance).filter(UserAlliance.alliance_id == alliance_id).first()
    return alliance_obj

def get_user_alliances_by_user(user_id: int, db: Session):
    alliances = db.query(UserAlliance).filter(UserAlliance.user_id == user_id).all()
    return alliances

def create_user_alliance(alliance: UserAlliance_schema, user_id: int, db: Session):
    alliance_obj = UserAlliance(**alliance.model_dump(), user_id=user_id)
    db.add(alliance_obj)
    db.commit()
    db.refresh(alliance_obj)
    return alliance_obj

def delete_user_alliance(alliance_id: int, db: Session):
    alliance_obj = db.query(UserAlliance).filter(UserAlliance.alliance_id == alliance_id).first()
    if alliance_obj:
        db.delete(alliance_obj)
        db.commit()
    return alliance_obj
