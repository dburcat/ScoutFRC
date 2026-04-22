from models import alliance
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

alliance_router = APIRouter(prefix="/alliances", tags=["alliances"])

@alliance_router.get("/")
def get_alliances(db: Session = Depends(get_db)):
        alliances = db.query(alliance.Alliance).all()
        return alliances