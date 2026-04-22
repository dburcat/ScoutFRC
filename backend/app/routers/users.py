from models import user
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

user_router = APIRouter(prefix="/users", tags=["users"])

@user_router.get("/")
def get_users(db: Session = Depends(get_db)):
    users = db.query(user.User).all()
    return users