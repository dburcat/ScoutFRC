from models import robot_performance
from db.session import get_session
from fastapi import APIRouter

robot_performance_router = APIRouter(prefix="/robot_performances", tags=["robot_performances"])

@robot_performance_router.get("/")
def get_robot_performances():
    with get_session() as session:
        robot_performances = session.query(robot_performance.RobotPerformance).all()
        return robot_performances