from app.schemas.robot_performance_schema import RobotPerformance_schema
from app.crud import crud_robot_performance
from app.db.session import get_db
from app.routers.deps import get_current_user
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

@robot_performance_router.get("/match/{match_id}", response_model=list[RobotPerformance_schema])
def get_robot_performances_by_match(match_id: int, db: Session = Depends(get_db)):
        robot_performances = crud_robot_performance.get_robot_performances_by_match(match_id, db)
        return robot_performances

@robot_performance_router.post("/", response_model=RobotPerformance_schema, status_code=201)
def create_robot_performance(
        robot_performance: RobotPerformance_schema,
        current_user = Depends(get_current_user),
        db: Session = Depends(get_db)
):
        # Only scouts and admins can create performances
        if current_user.role not in ["SCOUT", "COACH", "TEAM_ADMIN", "SYSTEM_ADMIN"]:
                raise HTTPException(status_code=403, detail="Not authorized to create robot performances")
        
        robot_performance_obj = crud_robot_performance.create_robot_performance(robot_performance, db)
        return robot_performance_obj