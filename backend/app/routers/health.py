import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from celery.result import AsyncResult
from app.db.session import get_db
from app.celery_app import celery_app
from app.tasks.sample import ping

logger = logging.getLogger(__name__)
health_router = APIRouter(tags=["health"])


def _broker_status() -> str:
    """Ping Redis broker. Returns 'healthy' or an error string."""
    try:
        conn = celery_app.connection_for_write()
        conn.ensure_connection(max_retries=1)
        conn.release()
        return "healthy"
    except Exception as exc:
        return f"unhealthy: {exc}"


@health_router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check — verifies database and Redis broker connectivity."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    broker_status = _broker_status()

    overall = "healthy" if db_status == "healthy" and broker_status == "healthy" else "degraded"
    return {
        "status": overall,
        "database": db_status,
        "broker": broker_status,
    }


@health_router.post("/health/celery")
def dispatch_test_task():
    """Dispatch a ping task and return its task ID for verification."""
    result = ping.delay()
    return {"task_id": result.id, "status": "dispatched"}


@health_router.get("/health/celery/{task_id}")
def get_task_result(task_id: str):
    """Poll the result of a previously dispatched task."""
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "state": result.state,
        "result": result.result if result.ready() else None,
    }