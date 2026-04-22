from sqlalchemy.orm import Session
from models import User

def get_users(db: Session):
        users = db.query(User).all()
        return users

def get_user(user_id: int, db: Session):
        user_obj = db.query(User).filter(User.user_id == user_id).first()
        return user_obj