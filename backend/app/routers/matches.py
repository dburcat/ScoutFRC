from models import match
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

match_router = APIRouter(prefix="/matches", tags=["matches"])

@match_router.get("/")
def get_matches(db: Session = Depends(get_db)):
        matches = db.query(match.Match).all()
        return matches