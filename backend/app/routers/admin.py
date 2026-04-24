# backend/app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.integrations import tba_client, tba_mapper

admin_router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


@admin_router.post("/sync-event/{event_key}")
def sync_event(
    event_key: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    # 1. Fetch from TBA
    try:
        tba_event   = tba_client.get_event(event_key)
        tba_teams   = tba_client.get_event_teams(event_key)
        tba_matches = tba_client.get_event_matches(event_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 2. Upsert Event
    event = tba_mapper.upsert_event(db, tba_event)

    # 3. Upsert Teams, build lookup map
    team_number_to_id: dict[int, int] = {}
    for tba_team in tba_teams:
        team = tba_mapper.upsert_team(db, tba_team)
        team_number_to_id[tba_team["team_number"]] = team.team_id

    # 4. Upsert Matches + Alliances + RobotPerformances
    synced_matches = 0
    for tba_match in tba_matches:
        tba_mapper.upsert_match(db, tba_match, event, team_number_to_id)
        synced_matches += 1

    db.commit()

    return {
        "status": "ok",
        "event_key": event_key,
        "teams_synced": len(tba_teams),
        "matches_synced": synced_matches,
    }