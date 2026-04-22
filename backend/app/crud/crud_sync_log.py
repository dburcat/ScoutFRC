from sqlalchemy.orm import Session
from models import SyncLog

def get_sync_logs(db: Session):
        sync_logs = db.query(SyncLog).all()
        return sync_logs

def get_sync_log(sync_log_id: int, db: Session):
        sync_log_obj = db.query(SyncLog).filter(SyncLog.sync_id == sync_log_id).first()
        return sync_log_obj