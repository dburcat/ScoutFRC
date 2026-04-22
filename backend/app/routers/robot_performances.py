from models import robot_performance
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

robot_performance_router = APIRouter(prefix="/robot_performances", tags=["robot_performances"])

@robot_performance_router.get("/")
def get_robot_performances(db: Session = Depends(get_db)):
        robot_performances = db.query(robot_performance.RobotPerformance).all()
        return robot_performances