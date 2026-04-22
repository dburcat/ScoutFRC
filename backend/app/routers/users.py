from schema.user_schema import User_schema
from crud import crud_user
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

user_router = APIRouter(prefix="/users", tags=["users"])

@user_router.get("/", response_model=list[User_schema])
def get_users(db: Session = Depends(get_db)):
    users = crud_user.get_users(db)
    return users

@user_router.get("/{user_id}", response_model=User_schema)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user_obj = crud_user.get_user(user_id, db)
    if user_obj is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_obj