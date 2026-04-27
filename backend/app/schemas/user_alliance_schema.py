from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserAllianceBase(BaseModel):
    name: Optional[str] = None
    red_teams: str  # Comma-separated: "1234,4567,7890"
    blue_teams: str  # Comma-separated: "2345,5678,8901"

class UserAllianceCreate(UserAllianceBase):
    pass

class UserAlliance_schema(UserAllianceBase):
    alliance_id: int
    user_id: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
