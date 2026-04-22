from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class SyncLogBase(BaseModel):
    sync_type: str
    resource_id: str
    status: str = "success"
    records_created: int = 0
    records_updated: int = 0
    error_message: Optional[str] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None

class SyncLog(SyncLogBase):
    sync_id: int
    sync_timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)