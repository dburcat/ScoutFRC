# backend/app/integrations/tba_mapper.py
import logging
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text
from app.models import Event, Team, Match, Alliance, RobotPerformance

logger = logging.getLogger(__name__)

MATCH_TYPE_MAP = {
    "qm": "qualification",
    "sf": "semifinal",
    "f":  "final",
    "ef": "semifinal",   # Einstein elim rounds, map to semifinal
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def truncate(value: str | None, max_length: int) -> str | None:
    """Truncate string to max_length, return None if input is None."""
    if value is None:
        return None
    return value[:max_length] if len(value) > max_length else value


def extract_match_number(match_number_str: str | int) -> int:
    """Extract numeric part from match number (e.g., '229B' -> 229)."""
    try:
        if isinstance(match_number_str, int):
            return match_number_str
        
        # Remove non-digit characters from the end (e.g., 'B', 'A', etc.)
        numeric_part = ""
        for char in str(match_number_str):
            if char.isdigit():
                numeric_part += char
            else:
                # Stop at first non-digit and use what we have
                break
        
        result = int(numeric_part) if numeric_part else 0
        if result == 0:
            logger.warning("extract_match_number(%s) resulted in 0, original: %s", match_number_str, match_number_str)
        return result
    except Exception as e:
        logger.error("extract_match_number failed for %s: %s", match_number_str, e)
        return 0

# ── Event ────────────────────────────────────────────────────────────────────

def upsert_event(db: Session, tba_event: dict) -> Event:
    # Try to get existing event
    event = db.query(Event).filter(Event.tba_event_key == tba_event["key"]).first()
    
    # Truncate fields to fit column constraints (schema doesn't specify max lengths, use reasonable defaults)
    name = truncate(tba_event.get("name"), 255)
    city = truncate(tba_event.get("city"), 100)
    state_prov = truncate(tba_event.get("state_prov"), 60)
    country = truncate(tba_event.get("country"), 60)
    
    if event:
        # Update existing
        event.name = name
        event.city = city
        event.state_prov = state_prov
        event.country = country
        event.start_date = date.fromisoformat(tba_event["start_date"])
        event.end_date = date.fromisoformat(tba_event["end_date"])
        db.flush()
    else:
        # Create new
        event = Event(
            tba_event_key=tba_event["key"],
            name=name,
            city=city,
            state_prov=state_prov,
            country=country,
            start_date=date.fromisoformat(tba_event["start_date"]),
            end_date=date.fromisoformat(tba_event["end_date"]),
            season_year=tba_event["year"],
        )
        db.add(event)
        db.flush()
    return event


# ── Teams ────────────────────────────────────────────────────────────────────

def upsert_team(db: Session, tba_team: dict) -> Team:
    # Try to get existing team
    team = db.query(Team).filter(Team.team_number == tba_team["team_number"]).first()
    
    # Truncate fields to fit column constraints
    team_name = truncate(tba_team.get("nickname"), 255)
    school_name = truncate(tba_team.get("school_name"), 200)
    city = truncate(tba_team.get("city"), 100)
    state_prov = truncate(tba_team.get("state_prov"), 60)
    country = truncate(tba_team.get("country"), 60)
    
    if team:
        # Update existing
        team.team_name = team_name
        team.school_name = school_name
        team.city = city
        team.state_prov = state_prov
        team.country = country
        team.rookie_year = tba_team.get("rookie_year")
        db.flush()
    else:
        # Create new
        team = Team(
            team_number=tba_team["team_number"],
            team_name=team_name,
            school_name=school_name,
            city=city,
            state_prov=state_prov,
            country=country,
            rookie_year=tba_team.get("rookie_year"),
        )
        db.add(team)
        db.flush()
    return team


# ── Matches, Alliances, RobotPerformances ────────────────────────────────────

def upsert_match(
    db: Session,
    tba_match: dict,
    event: Event,
    team_number_to_id: dict[int, int],   # team_number → team_id
) -> Match:
    comp_level = tba_match.get("comp_level", "qm")
    match_type = MATCH_TYPE_MAP.get(comp_level, "qualification")

    played_at = None
    if tba_match.get("time"):
        played_at = datetime.fromtimestamp(tba_match["time"], tz=timezone.utc)

    # Pick first video if available
    videos = tba_match.get("videos", [])
    video_url = None
    if videos:
        v = videos[0]
        if v.get("type") == "youtube":
            video_url = f"https://www.youtube.com/watch?v={v['key']}"
        else:
            video_url = v.get("key")

    # Upsert the Match row
    match = db.query(Match).filter(Match.tba_match_key == tba_match["key"]).first()
    match_number = extract_match_number(tba_match["match_number"])
    
    if match:
        # Update existing
        match.match_type = match_type
        match.match_number = match_number
        match.played_at = played_at
        match.video_url = video_url
        db.flush()
    else:
        # Create new
        match = Match(
            event_id=event.event_id,
            tba_match_key=tba_match["key"],
            match_type=match_type,
            match_number=match_number,
            played_at=played_at,
            video_url=video_url,
            processing_status="pending",
        )
        db.add(match)
        db.flush()

    # Wipe old alliances/performances so we can re-insert cleanly on re-sync
    # Explicitly delete robot_performances first to avoid cascade delete issues
    db.query(RobotPerformance).filter(RobotPerformance.match_id == match.match_id).delete()
    db.query(Alliance).filter(Alliance.match_id == match.match_id).delete()
    db.flush()

    # Build Alliance + RobotPerformance rows
    winning_color = tba_match.get("winning_alliance", "")  # "red", "blue", or ""
    alliances_data = tba_match.get("alliances", {})

    for color in ("red", "blue"):
        alliance_data = alliances_data.get(color, {})
        score = alliance_data.get("score", None)
        if score == -1:
            score = None  # TBA returns -1 for unplayed matches

        alliance = Alliance(
            match_id=match.match_id,
            color=color,
            total_score=score,
            won=(color == winning_color) if winning_color else None,
        )
        db.add(alliance)
        db.flush()  # need alliance_id for RobotPerformance FK

        team_keys = alliance_data.get("team_keys", [])  # ["frc254", "frc971", "frc1678"]
        seen_teams = set()  # Track teams we've already added to this match
        for position, team_key in enumerate(team_keys[:3], start=1):
            # Extract numeric part from team_key (e.g., "frc254", "frc254B" -> 254)
            try:
                team_str = team_key.replace("frc", "")
                team_number = extract_match_number(team_str)  # Use existing helper for consistency
                if team_number == 0:
                    logger.warning("team_key %s resulted in team_number 0, skipping", team_key)
                    continue
            except Exception as e:
                logger.error("Failed to parse team_key %s: %s", team_key, e)
                continue
            
            team_id = team_number_to_id.get(team_number)
            if team_id is None:
                continue  # team wasn't in event teams list (shouldn't happen)
            
            # Skip if we've already added this team to this match (TBA data sometimes has duplicates)
            if team_id in seen_teams:
                logger.warning(
                    "Skipping duplicate team %d (team_key %s) in match %s, color %s",
                    team_number, team_key, match.tba_match_key, color
                )
                continue
            seen_teams.add(team_id)

            perf = RobotPerformance(
                match_id=match.match_id,
                team_id=team_id,
                alliance_id=alliance.alliance_id,
                alliance_position=position,
                auto_score=0,
                teleop_score=0,
                endgame_score=0,
                fouls_drawn=0,
                fouls_committed=0,
                no_show=False,
                disabled=False,
            )
            db.add(perf)

    db.flush()
    return match