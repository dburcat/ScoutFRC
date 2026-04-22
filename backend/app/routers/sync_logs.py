from models import sync_log
from db.session import get_session
from fastapi import APIRouter

sync_log_router = APIRouter(prefix="/sync_logs", tags=["sync_logs"])

@sync_log_router.get("/")
def get_sync_logs():
    with get_session() as session:
        sync_logs = session.query(sync_log.SyncLog).all()
        return sync_logs