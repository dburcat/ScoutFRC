from sqlalchemy.orm import Session
from app.models import User
from app.core.security import verify_password
from typing import Optional

def get_users(db: Session):
        users = db.query(User).all()
        return users

def get_user(user_id: int, db: Session):
        user_obj = db.query(User).filter(User.user_id == user_id).first()
        return user_obj

def create_user(user: User, db: Session):
        hashed_password = user.hashed_password # In a real application, you should hash the password before storing it
        user.hashed_password = hashed_password
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate(db: Session, *, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user