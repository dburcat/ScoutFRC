from models import alliance
from schema.alliance_schema import Alliance_schema
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

alliance_router = APIRouter(prefix="/alliances", tags=["alliances"])

@alliance_router.get("/", response_model=list[Alliance_schema])
def get_alliances(db: Session = Depends(get_db)):
        alliances = db.query(alliance.Alliance).all()
        return alliances

@alliance_router.get("/{alliance_id}", response_model=Alliance_schema)
def get_alliance(alliance_id: int, db: Session = Depends(get_db)):
        alliance_obj = db.query(alliance.Alliance).filter(alliance.Alliance.alliance_id == alliance_id).first()
        if alliance_obj is None:
                raise HTTPException(status_code=404, detail="Alliance not found")
        return alliance_obj