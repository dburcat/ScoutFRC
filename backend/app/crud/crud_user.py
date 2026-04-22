from sqlalchemy.orm import Session
from app.models import User

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