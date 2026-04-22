from pydantic import BaseModel, ConfigDict
from typing import Optional
from .robot_performance_schema import RobotPerformance

class AllianceBase(BaseModel):
    match_id: int
    color: str # 'red' or 'blue'
    total_score: Optional[int] = None
    rp_earned: Optional[int] = None
    won: Optional[bool] = None

class AllianceCreate(AllianceBase):
    pass

class Alliance(AllianceBase):
    alliance_id: int
    # Optional: Include robot performances if you want nested data
    robot_performances: list[RobotPerformance] = []
    
    model_config = ConfigDict(from_attributes=True)