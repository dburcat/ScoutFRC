from sqlalchemy.orm import Session
from app.models import SyncLog


def get_sync_logs(db: Session):
    sync_logs = db.query(SyncLog).all()
    return sync_logs


def get_sync_log(sync_log_id: int, db: Session):
    sync_log_obj = db.query(SyncLog).filter(SyncLog.sync_id == sync_log_id).first()
    return sync_log_obj


def create_sync_log(
    db: Session,
    sync_type: str,
    resource_id: str,
    status: str,
    triggered_by: int | None = None,
    records_created: int = 0,
    records_updated: int = 0,
    error_message: str | None = None,
    new_values: dict | None = None,
) -> SyncLog:
    log = SyncLog(
        sync_type=sync_type,
        resource_id=resource_id,
        status=status,
        triggered_by=triggered_by,
        records_created=records_created,
        records_updated=records_updated,
        error_message=error_message,
        new_values=new_values,
    )
    db.add(log)
    return log