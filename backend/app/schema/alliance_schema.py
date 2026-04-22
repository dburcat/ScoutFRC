from pydantic import BaseModel, ConfigDict
from typing import Optional
from .robot_performance_schema import RobotPerformance_schema

class AllianceBase(BaseModel):
    match_id: int
    color: str # 'red' or 'blue'
    total_score: Optional[int] = None
    rp_earned: Optional[int] = None
    won: Optional[bool] = None

class AllianceCreate(AllianceBase):
    pass

class Alliance_schema(AllianceBase):
    alliance_id: int
    # Optional: Include robot performances if you want nested data
    robot_performances: list[RobotPerformance_schema] = []
    
    model_config = ConfigDict(from_attributes=True)