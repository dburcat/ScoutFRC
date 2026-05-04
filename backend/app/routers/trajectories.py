"""
Trajectories and heatmaps API endpoints.

GET /matches/{id}/trajectories       — Get all team trajectories for a match
GET /matches/{id}/heatmap            — Get heatmap data for a match
GET /matches/{id}/trajectories/phase — Get trajectories for specific phase
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.routers.deps import get_db, get_current_user
from app.services.trajectory_processor import TrajectoryProcessor
from app.services.heatmap_generator import HeatmapGenerator
from app.services.field_definitions import get_field_layout
from app.models import Match

trajectories_router = APIRouter(tags=["trajectories"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class TrajectoryPoint(BaseModel):
    x: float
    y: float
    timestamp_ms: int | None = None


class TeamTrajectory(BaseModel):
    team_id: int
    alliance: str  # red or blue
    coordinates: list[tuple[float, float]]
    stats: dict


class HeatmapBinResponse(BaseModel):
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    center_x: float
    center_y: float
    count: int
    intensity: int


class MatchHeatmapResponse(BaseModel):
    match_id: int
    field_width: float
    field_height: float
    bins: list[HeatmapBinResponse]
    max_intensity: int
    total_points: int


class MatchTrajectoriesResponse(BaseModel):
    match_id: int
    teams: dict[int, TeamTrajectory]
    field_width: float
    field_height: float


# ── Endpoints ──────────────────────────────────────────────────────────────────

@trajectories_router.get("/matches/{match_id}/trajectories")
def get_match_trajectories(
    match_id: int,
    phase: str = Query("all", description="Phase filter: all, auto, teleop, endgame"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MatchTrajectoriesResponse:
    """
    Get all robot trajectories for a match.
    
    **Parameters:**
    - `match_id`: Match ID
    - `phase`: Filter by game phase (auto, teleop, endgame, or all)
    
    **Response:**
    - `teams`: Dictionary mapping team_id to trajectory data
    - Field dimensions and metadata
    """
    # Verify match exists
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Get field layout (default to 2024 for now; could infer from event)
    field = get_field_layout(2024)

    # Get trajectories
    processor = TrajectoryProcessor(db)
    trajectories = processor.get_match_trajectories(match_id)

    # Filter by phase if needed
    if phase != "all":
        if phase not in ["auto", "teleop", "endgame"]:
            raise HTTPException(status_code=422, detail="Invalid phase")
        
        phase_trajectories = processor.get_phase_trajectories(match_id, phase)
        for team_id in trajectories:
            trajectories[team_id]["coordinates"] = phase_trajectories.get(team_id, [])

    # Format response
    teams_data = {}
    for team_id, traj in trajectories.items():
        teams_data[team_id] = TeamTrajectory(
            team_id=team_id,
            alliance="red" if team_id % 2 == 0 else "blue",  # Simple heuristic
            coordinates=traj["all_coordinates"],
            stats=traj["stats"],
        )

    return MatchTrajectoriesResponse(
        match_id=match_id,
        teams=teams_data,
        field_width=field.width_ft,
        field_height=field.height_ft,
    )


@trajectories_router.get("/matches/{match_id}/heatmap")
def get_match_heatmap(
    match_id: int,
    phase: str = Query("all", description="Phase filter: all, auto, teleop, endgame"),
    team_id: int | None = Query(None, description="Optional: filter to single team"),
    bin_size: float = Query(1.0, description="Heatmap bin size in feet"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MatchHeatmapResponse:
    """
    Get spatial heatmap data for a match.
    
    **Parameters:**
    - `match_id`: Match ID
    - `phase`: Game phase (auto, teleop, endgame, or all)
    - `team_id`: Optional single team filter
    - `bin_size`: Grid cell size in feet (default: 1.0)
    
    **Response:**
    - `bins`: Array of non-empty heatmap cells with intensity
    - `max_intensity`: Maximum count in any bin
    """
    # Verify match exists
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Get field layout
    field = get_field_layout(2024)

    # Get trajectories
    processor = TrajectoryProcessor(db)
    
    if team_id:
        traj = processor.get_team_trajectory(match_id, team_id)
        if not traj:
            raise HTTPException(status_code=404, detail="Team trajectory not found")
        
        if phase == "all":
            coordinates = traj["all_coordinates"]
        else:
            coordinates = traj["phases"].get(phase, [])
    else:
        phase_trajs = processor.get_phase_trajectories(match_id, phase)
        coordinates = []
        for coords in phase_trajs.values():
            coordinates.extend(coords)

    # Generate heatmap
    generator = HeatmapGenerator(
        field_width=field.width_ft,
        field_height=field.height_ft,
        bin_size=bin_size,
    )
    
    bins = generator.generate_heatmap(coordinates)
    max_intensity = max((b.count for b in bins), default=0)

    # Format response
    bins_response = [
        HeatmapBinResponse(
            x_min=b.x_min,
            x_max=b.x_max,
            y_min=b.y_min,
            y_max=b.y_max,
            center_x=b.center_x,
            center_y=b.center_y,
            count=b.count,
            intensity=b.count,
        )
        for b in bins
    ]

    return MatchHeatmapResponse(
        match_id=match_id,
        field_width=field.width_ft,
        field_height=field.height_ft,
        bins=bins_response,
        max_intensity=int(max_intensity),
        total_points=len(coordinates),
    )


@trajectories_router.get("/matches/{match_id}/field-layout")
def get_match_field_layout(
    match_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get field layout and zone definitions for a match.
    
    Useful for rendering field diagram and scoring zones.
    """
    # Verify match exists
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Get field layout (could infer year from event; using 2024 for now)
    field = get_field_layout(2024)

    return field.to_dict()
