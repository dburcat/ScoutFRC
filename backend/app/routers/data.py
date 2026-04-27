import json
import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.routers.deps import get_current_user
from app.crud import crud_scouting_observation, crud_team, crud_match
from app.schemas.scouting_observation_schema import ScoutingObservation_schema
from app.models import ScoutingObservation, Team, Match, Alliance

data_router = APIRouter(prefix="/data", tags=["data"])

# Bulk submission endpoint
@data_router.post("/bulk-observations", response_model=list[ScoutingObservation_schema], status_code=201)
def bulk_submit_observations(
    observations: list[ScoutingObservation_schema],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit multiple observations at once (up to 50 per request)"""
    if len(observations) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 observations per request")
    
    if current_user.role not in ["SCOUT", "COACH", "TEAM_ADMIN", "SYSTEM_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized to submit observations")
    
    created = []
    for obs in observations:
        obj = ScoutingObservation(**obs.model_dump())
        db.add(obj)
        created.append(obj)
    
    db.commit()
    for obj in created:
        db.refresh(obj)
    
    return created


# CSV Export endpoint
@data_router.get("/events/{event_id}/export/csv")
def export_event_rankings_csv(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Export event rankings as CSV"""
    teams = db.query(Team).join(Match).filter(Match.event_id == event_id).distinct().all()
    
    if not teams:
        raise HTTPException(status_code=404, detail="No teams found for this event")
    
    # Build CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Team Number", "Team Name", "Matches Played", "Wins", "Avg Score", "Win %"])
    
    for idx, team in enumerate(sorted(teams, key=lambda t: t.team_number), 1):
        matches = db.query(Match).join(Alliance).filter(
            Match.event_id == event_id,
            Alliance.teams.any(team_id=team.team_id)
        ).all()
        
        if not matches:
            continue
        
        wins = sum(1 for m in matches if any(a.won for a in m.alliances if any(t.team_id == team.team_id for t in a.teams)))
        avg_score = sum((a.total_score or 0) for m in matches for a in m.alliances if any(t.team_id == team.team_id for t in a.teams)) // len(matches) if matches else 0
        
        writer.writerow([
            team.team_number,
            team.team_name or "",
            len(matches),
            wins,
            avg_score,
            f"{(wins/len(matches)*100):.1f}%" if matches else "0%"
        ])
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=event_{event_id}_rankings.csv"}
    )


# JSON Export endpoint
@data_router.get("/events/{event_id}/export/json")
def export_event_data_json(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Export full event data as JSON"""
    event = db.query(Match).filter(Match.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    matches = db.query(Match).filter(Match.event_id == event_id).all()
    teams = db.query(Team).join(Match).filter(Match.event_id == event_id).distinct().all()
    
    export_data = {
        "event_id": event_id,
        "teams": [
            {
                "team_id": t.team_id,
                "team_number": t.team_number,
                "team_name": t.team_name,
            }
            for t in teams
        ],
        "matches_count": len(matches),
        "export_timestamp": str(func.now())
    }
    
    return export_data
