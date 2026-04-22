from sqlalchemy.orm import Session
from models import RobotPerformance
from schema.robot_performance_schema import RobotPerformance_schema

def get_robot_performances(db: Session):
        robot_performances = db.query(RobotPerformance).all()
        return robot_performances

def get_robot_performance(robot_performance_id: int, db: Session):
        robot_performance_obj = db.query(RobotPerformance).filter(RobotPerformance.perf_id == robot_performance_id).first()
        return robot_performance_obj

def get_robot_performances_by_match(match_id: int, db: Session):
        robot_performances = db.query(RobotPerformance).filter(RobotPerformance.match_id == match_id).all()
        return robot_performances

def create_robot_performance(robot_performance: RobotPerformance_schema, db: Session):
        robot_performance_obj = RobotPerformance(**robot_performance.model_dump())
        db.add(robot_performance_obj)
        db.commit()
        db.refresh(robot_performance_obj)
        return robot_performance_obj