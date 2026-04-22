from sqlalchemy.orm import Session
from models import Alliance

def get_alliances(db: Session):
        alliances = db.query(Alliance).all()
        return alliances

def get_alliance(alliance_id: int, db: Session):
        alliance_obj = db.query(Alliance).filter(Alliance.alliance_id == alliance_id).first()
        return alliance_obj