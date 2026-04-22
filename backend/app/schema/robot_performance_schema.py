from pydantic import BaseModel, ConfigDict
from typing import Optional

class RobotPerformanceBase(BaseModel):
    match_id: int
    team_id: int
    alliance_id: int
    alliance_position: int
    track_id: Optional[int] = None
    auto_score: int = 0
    teleop_score: int = 0
    endgame_score: int = 0
    fouls_drawn: int = 0
    fouls_committed: int = 0

class RobotPerformanceCreate(RobotPerformanceBase):
    pass

class RobotPerformance(RobotPerformanceBase):
    perf_id: int
    total_score_contribution: int
    
    model_config = ConfigDict(from_attributes=True)