from models import user
from db.session import get_session
from fastapi import APIRouter

user_router = APIRouter(prefix="/users", tags=["users"])

@user_router.get("/")
def get_users():
    with get_session() as session:
        users = session.query(user.User).all()
        return users