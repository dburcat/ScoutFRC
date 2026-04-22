from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class MatchBase(BaseModel):
    event_id: int
    tba_match_key: str
    match_type: str # 'qualification', 'semifinal', 'final'
    match_number: int
    video_url: Optional[str] = None
    processing_status: str = "pending"
    played_at: Optional[datetime] = None

class MatchCreate(MatchBase):
    pass

class Match_schema(MatchBase):
    match_id: int
    created_at: datetime
    # Use forward references for nesting if Alliance depends on Match
    alliances: List["Alliance_schema"] = [] 
    
    model_config = ConfigDict(from_attributes=True)

# This handles circular imports if Match and Alliance reference each other
from .alliance_schema import Alliance_schema
Match_schema.model_rebuild()