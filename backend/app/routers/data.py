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
from app.models import ScoutingObservation, Team, Match, Alliance, Event

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
    from sqlalchemy import select
    
    # Get all teams that participated in this event
    teams_query = db.query(Team).join(
        Team.robot_performances
    ).join(
        Alliance
    ).filter(
        Alliance.match_id.in_(
            db.query(Match.match_id).filter(Match.event_id == event_id)
        )
    ).distinct()
    
    teams = teams_query.all()
    
    if not teams:
        raise HTTPException(status_code=404, detail="No teams found for this event")
    
    # Build CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Team Number", "Team Name", "Matches Played", "Wins", "Avg Score", "Win %"])
    
    for team in sorted(teams, key=lambda t: t.team_number):
        # Get all matches for this team in this event
        team_matches = db.query(Match).join(
            Alliance
        ).join(
            Team.robot_performances
        ).filter(
            Match.event_id == event_id,
            Team.team_id == team.team_id
        ).distinct().all()
        
        if not team_matches:
            continue
        
        # Calculate stats
        wins = 0
        total_score = 0
        
        for match in team_matches:
            for alliance in match.alliances:
                for rob_perf in alliance.robot_performances:
                    if rob_perf.team_id == team.team_id:
                        if alliance.won:
                            wins += 1
                        total_score += alliance.total_score or 0
        
        avg_score = total_score // len(team_matches) if team_matches else 0
        win_pct = (wins / len(team_matches) * 100) if team_matches else 0
        
        writer.writerow([
            team.team_number,
            team.team_name or "",
            len(team_matches),
            wins,
            avg_score,
            f"{win_pct:.1f}%"
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
    from datetime import datetime
    
    # Check if event exists
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    matches = db.query(Match).filter(Match.event_id == event_id).all()
    teams = db.query(Team).join(
        Team.robot_performances
    ).join(
        Alliance
    ).filter(
        Alliance.match_id.in_(
            db.query(Match.match_id).filter(Match.event_id == event_id)
        )
    ).distinct().all()
    
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
        "export_timestamp": datetime.utcnow().isoformat()
    }
    
    return export_data
