from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: str
    role: str = "SCOUT"
    team_id: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str # Used for registration only

class User_schema(UserBase):
    user_id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)