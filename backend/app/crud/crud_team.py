from sqlalchemy.orm import Session
from app.models import Team, RobotPerformance, Match

def get_teams(db: Session, team_number: int | None = None, skip: int = 0, limit: int = 100):
        q = db.query(Team)
        if team_number is not None:
                q = q.filter(Team.team_number == team_number)
        teams = q.offset(skip).limit(limit).all()
        return teams

def get_teams_count(db: Session, team_number: int | None = None) -> int:
        q = db.query(Team)
        if team_number is not None:
                q = q.filter(Team.team_number == team_number)
        return q.count()

def get_team(team_id: int, db: Session):
        team_obj = db.query(Team).filter(Team.team_id == team_id).first()
        return team_obj

def get_teams_by_event(event_id: int, db: Session, skip: int = 0, limit: int = 100):
        teams = (
        db.query(Team)
        .join(RobotPerformance)
        .join(Match)
        .filter(Match.event_id == event_id)
        .distinct()
        .offset(skip)
        .limit(limit)
        .all()
    )
        return teams

def get_team_matches(team_id: int, db: Session):
        matches = (
        db.query(Match)
        .join(RobotPerformance)
        .filter(RobotPerformance.team_id == team_id)
        .distinct()
        .all()
    )
        return matches