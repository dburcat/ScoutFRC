from schema.alliance_schema import Alliance_schema
from crud import crud_alliance
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

alliance_router = APIRouter(prefix="/alliances", tags=["alliances"])

@alliance_router.get("/", response_model=list[Alliance_schema])
def get_alliances(db: Session = Depends(get_db)):
        alliances = crud_alliance.get_alliances(db)
        return alliances

@alliance_router.get("/{alliance_id}", response_model=Alliance_schema)
def get_alliance(alliance_id: int, db: Session = Depends(get_db)):
        alliance_obj = crud_alliance.get_alliance(alliance_id, db)
        if alliance_obj is None:
                raise HTTPException(status_code=404, detail="Alliance not found")
        return alliance_obj

@alliance_router.post("/", response_model=Alliance_schema, status_code=201)
def create_alliance(alliance: Alliance_schema, db: Session = Depends(get_db)):
        alliance_obj = crud_alliance.create_alliance(alliance, db)
        return alliance_obj