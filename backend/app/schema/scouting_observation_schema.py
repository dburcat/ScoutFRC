from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ScoutingObservationBase(BaseModel):
    team_id: int
    match_id: int
    scout_id: int
    notes: Optional[str] = None
    rating: Optional[int] = None # 1-5
    actions: Optional[dict] = None

class ScoutingObservationCreate(ScoutingObservationBase):
    pass

class ScoutingObservation_schema(ScoutingObservationBase):
    observation_id: int
    submitted_at: datetime
    
    model_config = ConfigDict(from_attributes=True)