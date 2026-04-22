from pydantic import BaseModel, ConfigDict
from typing import Optional, Union
from datetime import date, datetime

class EventBase(BaseModel):
    tba_event_key: str
    name: str
    location: Optional[str] = None
    start_date: date
    end_date: date
    season_year: int
    perspective_matrix: Optional[Union[dict, list]] = None

class EventCreate(EventBase):
    pass

class Event(EventBase):
    event_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)