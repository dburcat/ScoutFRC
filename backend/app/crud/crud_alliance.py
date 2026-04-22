from sqlalchemy.orm import Session
from app.models import Alliance
from app.schemas.alliance_schema import Alliance_schema

def get_alliances(db: Session):
        alliances = db.query(Alliance).all()
        return alliances

def get_alliance(alliance_id: int, db: Session):
        alliance_obj = db.query(Alliance).filter(Alliance.alliance_id == alliance_id).first()
        return alliance_obj

def create_alliance(alliance: Alliance_schema, db: Session):
        alliance_obj = Alliance(**alliance.model_dump())
        db.add(alliance_obj)
        db.commit()
        db.refresh(alliance_obj)
        return alliance_obj