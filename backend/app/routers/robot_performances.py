from schema.robot_performance_schema import RobotPerformance_schema
from crud import crud_robot_performance
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

robot_performance_router = APIRouter(prefix="/robot_performances", tags=["robot_performances"])

@robot_performance_router.get("/", response_model=list[RobotPerformance_schema])
def get_robot_performances(db: Session = Depends(get_db)):
        robot_performances = crud_robot_performance.get_robot_performances(db)
        return robot_performances

@robot_performance_router.get("/{robot_performance_id}", response_model=RobotPerformance_schema)
def get_robot_performance(robot_performance_id: int, db: Session = Depends(get_db)):
        robot_performance_obj = crud_robot_performance.get_robot_performance(robot_performance_id, db)
        if robot_performance_obj is None:
                raise HTTPException(status_code=404, detail="Robot Performance not found")
        return robot_performance_obj