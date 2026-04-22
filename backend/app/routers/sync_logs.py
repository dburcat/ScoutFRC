from models import sync_log
from db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

sync_log_router = APIRouter(prefix="/sync_logs", tags=["sync_logs"])

@sync_log_router.get("/")
def get_sync_logs(db: Session = Depends(get_db)):
    sync_logs = db.query(sync_log.SyncLog).all()
    return sync_logs