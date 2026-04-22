from sqlalchemy.orm import Session
from models import RobotPerformance

def get_robot_performances(db: Session):
        robot_performances = db.query(RobotPerformance).all()
        return robot_performances

def get_robot_performance(robot_performance_id: int, db: Session):
        robot_performance_obj = db.query(RobotPerformance).filter(RobotPerformance.perf_id == robot_performance_id).first()
        return robot_performance_obj