from sqlalchemy.orm import Session
from app.models import User
from app.core.security import verify_password
from typing import Optional
from app.core.security import get_password_hash
from app.schemas.user_schema import UserCreate

def get_users(db: Session):
        users = db.query(User).all()
        return users

def get_user(user_id: int, db: Session):
        user_obj = db.query(User).filter(User.user_id == user_id).first()
        return user_obj

def create_user(db: Session, user_in: UserCreate):
    db_obj = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password), # BCrypt magic
        role=user_in.role
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()

def authenticate(db: Session, *, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user