from models import sync_log
from schema.sync_log_schema import SyncLog_schema
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

sync_log_router = APIRouter(prefix="/sync_logs", tags=["sync_logs"])

@sync_log_router.get("/", response_model=list[SyncLog_schema])
def get_sync_logs(db: Session = Depends(get_db)):
    sync_logs = db.query(sync_log.SyncLog).all()
    return sync_logs

@sync_log_router.get("/{sync_log_id}", response_model=SyncLog_schema)
def get_sync_log(sync_log_id: int, db: Session = Depends(get_db)):
    sync_log_obj = db.query(sync_log.SyncLog).filter(sync_log.SyncLog.sync_id == sync_log_id).first()
    if sync_log_obj is None:
        raise HTTPException(status_code=404, detail="Sync log not found")
    return sync_log_obj