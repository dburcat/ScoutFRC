from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TeamBase(BaseModel):
    team_number: int
    team_name: Optional[str] = None
    school_name: Optional[str] = None
    city: Optional[str] = None
    state_prov: Optional[str] = None
    country: Optional[str] = None
    rookie_year: Optional[int] = None

class TeamCreate(TeamBase):
    pass

class Team_schema(TeamBase):
    team_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)