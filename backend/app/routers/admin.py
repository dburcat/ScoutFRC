# backend/app/routers/admin.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.integrations.sync_service import sync_event, sync_season_events
from app.integrations.tba_client import check_api_key
from app.crud import crud_sync_log

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "SYSTEM_ADMIN":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


@admin_router.get("/check-tba")
def check_tba_endpoint(current_user: User = Depends(require_admin)):
    """Test TBA API key connectivity — call this to diagnose sync failures."""
    result = check_api_key()
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result["reason"])
    return result


@admin_router.post("/sync-season/{year}")
def sync_season_endpoint(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if year < 1992 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid season year")
    try:
        result = sync_season_events(db, year)
    except RuntimeError as e:
        logger.error("sync-season/%d failed: %s", year, e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("sync-season/%d unexpected error: %s", year, e)
        raise HTTPException(status_code=502, detail=str(e))
    return {"status": "ok", **result}


@admin_router.post("/sync-event/{event_key}")
def sync_event_endpoint(
    event_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        result = sync_event(db, event_key, triggered_by=current_user.user_id)
    except ValueError as e:
        logger.error("sync-event/%s not found: %s", event_key, e)
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error("sync-event/%s failed: %s", event_key, e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("sync-event/%s unexpected: %s", event_key, e)
        raise HTTPException(status_code=502, detail=str(e))
    return {"status": "ok", **result}


@admin_router.get("/scheduler/status")
def scheduler_status(current_user: User = Depends(require_admin)):
    from app.core.scheduler import _scheduler
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {"running": _scheduler.running, "jobs": jobs}