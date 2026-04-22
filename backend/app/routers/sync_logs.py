from schema.sync_log_schema import SyncLog_schema
from crud import crud_sync_log
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

sync_log_router = APIRouter(prefix="/sync_logs", tags=["sync_logs"])

@sync_log_router.get("/", response_model=list[SyncLog_schema])
def get_sync_logs(db: Session = Depends(get_db)):
    sync_logs = crud_sync_log.get_sync_logs(db)
    return sync_logs

@sync_log_router.get("/{sync_log_id}", response_model=SyncLog_schema)
def get_sync_log(sync_log_id: int, db: Session = Depends(get_db)):
    sync_log_obj = crud_sync_log.get_sync_log(sync_log_id, db)
    if sync_log_obj is None:
        raise HTTPException(status_code=404, detail="Sync log not found")
    return sync_log_obj