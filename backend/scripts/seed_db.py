from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import text

from app.db.database import engine
from app.db.session import SessionLocal
from app.models import Alliance, Base, Event, Match, RobotPerformance, ScoutingObservation, SyncLog, Team, User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def reset_tables() -> None:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE scouting_observation, sync_log, robot_performance, alliance, \"match\", event, team, \"user\" RESTART IDENTITY CASCADE"))


def seed() -> dict[str, int]:
    load_dotenv()
    session = SessionLocal()
    counts = {"events": 0, "teams": 0, "matches": 0, "alliances": 0, "robot_performances": 0, "users": 0, "observations": 0, "sync_logs": 0}

    try:
        reset_tables()

        event = Event(
            tba_event_key="2025scou",
            name="2025 ScouterFRC Showcase",
            location="Sample Arena, Long Beach, CA",
            start_date=date(2025, 3, 13),
            end_date=date(2025, 3, 16),
            season_year=2025,
            perspective_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        )
        session.add(event)
        session.flush()
        counts["events"] += 1

        teams: list[Team] = []
        for team_number in range(1678, 1708):
            team = Team(
                team_number=team_number,
                team_name=f"Team {team_number}",
                school_name=f"School {team_number}",
                city="Long Beach",
                state_prov="CA",
                country="USA",
                rookie_year=2000 + ((team_number - 1678) % 20),
            )
            session.add(team)
            teams.append(team)
        session.flush()
        counts["teams"] = len(teams)

        users: list[User] = []
        scout = User(
            username="scout1",
            email="scout1@scouterfrc.local",
            hashed_password=hash_password("password123"),
            team_id=teams[0].team_id,
            role="SCOUT",
            is_active=True,
            last_login=datetime.now(timezone.utc),
        )
        admin = User(
            username="admin",
            email="admin@scouterfrc.local",
            hashed_password=hash_password("password123"),
            team_id=None,
            role="SYSTEM_ADMIN",
            is_active=True,
            last_login=datetime.now(timezone.utc),
        )
        session.add_all([scout, admin])
        users.extend([scout, admin])
        session.flush()
        counts["users"] = len(users)

        matches: list[Match] = []
        for match_number in range(1, 13):
            match = Match(
                event_id=event.event_id,
                tba_match_key=f"2025scou_qm{match_number}",
                match_type="qualification",
                match_number=match_number,
                video_url=f"https://example.com/match/{match_number}",
                video_s3_key=None,
                processing_status="complete",
                played_at=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
            )
            session.add(match)
            matches.append(match)
        session.flush()
        counts["matches"] = len(matches)

        alliances: list[Alliance] = []
        performances: list[RobotPerformance] = []
        observations: list[ScoutingObservation] = []
        sync_logs: list[SyncLog] = []

        for index, match in enumerate(matches):
            red_teams = teams[(index * 3) % len(teams):(index * 3) % len(teams) + 3]
            blue_teams = teams[(index * 3 + 3) % len(teams):(index * 3 + 3) % len(teams) + 3]
            if len(red_teams) < 3:
                red_teams = teams[:3]
            if len(blue_teams) < 3:
                blue_teams = teams[3:6]

            red_score = 75 + index
            blue_score = 68 + index

            red_alliance = Alliance(match_id=match.match_id, color="red", total_score=red_score, rp_earned=2 if red_score >= blue_score else 1, won=red_score >= blue_score)
            blue_alliance = Alliance(match_id=match.match_id, color="blue", total_score=blue_score, rp_earned=2 if blue_score > red_score else 1, won=blue_score > red_score)
            session.add_all([red_alliance, blue_alliance])
            session.flush()
            alliances.extend([red_alliance, blue_alliance])

            for alliance, selected_teams in ((red_alliance, red_teams), (blue_alliance, blue_teams)):
                for position, team in enumerate(selected_teams, start=1):
                    performance = RobotPerformance(
                        match_id=match.match_id,
                        team_id=team.team_id,
                        alliance_id=alliance.alliance_id,
                        alliance_position=position,
                        track_id=(index * 6) + position,
                        auto_score=10 + position,
                        teleop_score=20 + position,
                        endgame_score=5 + position,
                        fouls_drawn=position - 1,
                        fouls_committed=0,
                        no_show=False,
                        disabled=False,
                    )
                    session.add(performance)
                    performances.append(performance)

            observations.append(
                ScoutingObservation(
                    team_id=red_teams[0].team_id,
                    match_id=match.match_id,
                    scout_id=scout.user_id,
                    notes=f"Strong autonomous for match {match.match_number}",
                    rating=4,
                    actions={"auto": {"mobility": True, "notes_scored": 3}, "teleop": {"notes_scored": 8}},
                )
            )

            sync_logs.append(
                SyncLog(
                    sync_type="match",
                    resource_id=match.tba_match_key,
                    status="success",
                    records_created=8,
                    records_updated=0,
                    old_values=None,
                    new_values={"match_number": match.match_number, "status": match.processing_status},
                    error_message=None,
                    triggered_by=admin.user_id,
                )
            )

        session.add_all(observations + sync_logs)
        session.commit()

        counts["alliances"] = len(alliances)
        counts["robot_performances"] = len(performances)
        counts["observations"] = len(observations)
        counts["sync_logs"] = len(sync_logs)
        return counts
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    results = seed()
    print("Seed complete")
    for key, value in results.items():
        print(f"{key}: {value}")