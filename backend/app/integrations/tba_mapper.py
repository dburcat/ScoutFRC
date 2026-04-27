# backend/app/integrations/tba_mapper.py
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models import Event, Team, Match, Alliance, RobotPerformance

MATCH_TYPE_MAP = {
    "qm": "qualification",
    "sf": "semifinal",
    "f":  "final",
    "ef": "semifinal",   # Einstein elim rounds, map to semifinal
}

# ── Event ────────────────────────────────────────────────────────────────────

def upsert_event(db: Session, tba_event: dict) -> Event:
    stmt = (
        pg_insert(Event)
        .values(
            tba_event_key=tba_event["key"],
            name=tba_event["name"],
            city=tba_event.get("city"),
            state_prov=tba_event.get("state_prov"),
            country=tba_event.get("country"),
            start_date=date.fromisoformat(tba_event["start_date"]),
            end_date=date.fromisoformat(tba_event["end_date"]),
            season_year=tba_event["year"],
        )
        .on_conflict_do_update(
            index_elements=["tba_event_key"],
            set_={
                Event.name:       tba_event["name"],
                Event.city:       tba_event.get("city"),
                Event.state_prov: tba_event.get("state_prov"),
                Event.country:    tba_event.get("country"),
                Event.start_date: date.fromisoformat(tba_event["start_date"]),
                Event.end_date:   date.fromisoformat(tba_event["end_date"]),
            },
        )
        .returning(Event.event_id)
    )
    row = db.execute(stmt).fetchone()
    db.flush()
    if row is None:
        raise ValueError("Failed to upsert event")
    event = db.get(Event, row[0])
    if event is None:
        raise ValueError("Failed to retrieve event after upsert")
    return event


# ── Teams ────────────────────────────────────────────────────────────────────

def upsert_team(db: Session, tba_team: dict) -> Team:
    stmt = (
        pg_insert(Team)
        .values(
            team_number=tba_team["team_number"],
            team_name=tba_team.get("nickname"),
            school_name=tba_team.get("school_name"),
            city=tba_team.get("city"),
            state_prov=tba_team.get("state_prov"),
            country=tba_team.get("country"),
            rookie_year=tba_team.get("rookie_year"),
        )
        .on_conflict_do_update(
            index_elements=["team_number"],
            set_={
                Team.team_name:   tba_team.get("nickname"),
                Team.school_name: tba_team.get("school_name"),
                Team.city:        tba_team.get("city"),
                Team.state_prov:  tba_team.get("state_prov"),
                Team.country:     tba_team.get("country"),
                Team.rookie_year: tba_team.get("rookie_year"),
            },
        )
        .returning(Team.team_id)
    )
    row = db.execute(stmt).fetchone()
    db.flush()
    if row is None:
        raise ValueError("Failed to upsert team")
    team = db.get(Team, row[0])
    if team is None:
        raise ValueError("Failed to retrieve team after upsert")
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
    stmt = (
        pg_insert(Match)
        .values(
            event_id=event.event_id,
            tba_match_key=tba_match["key"],
            match_type=match_type,
            match_number=tba_match["match_number"],
            played_at=played_at,
            video_url=video_url,
            processing_status="pending",
        )
        .on_conflict_do_update(
            index_elements=["tba_match_key"],
            set_={
                Match.match_type:   match_type,
                Match.match_number: tba_match["match_number"],
                Match.played_at:    played_at,
                Match.video_url:    video_url,
            },
        )
        .returning(Match.match_id)
    )
    row = db.execute(stmt).fetchone()
    db.flush()
    if row is None:
        raise ValueError("Failed to upsert match")
    match = db.get(Match, row[0])
    if match is None:
        raise ValueError("Failed to retrieve match after upsert")

    # Wipe old alliances/performances so we can re-insert cleanly on re-sync
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
        for position, team_key in enumerate(team_keys[:3], start=1):
            team_number = int(team_key.replace("frc", ""))
            team_id = team_number_to_id.get(team_number)
            if team_id is None:
                continue  # team wasn't in event teams list (shouldn't happen)

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