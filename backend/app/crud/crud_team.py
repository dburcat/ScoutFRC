from sqlalchemy.orm import Session
from app.models import Team, RobotPerformance, Match

def get_teams(db: Session):
        teams = db.query(Team).all()
        return teams

def get_team(team_id: int, db: Session):
        team_obj = db.query(Team).filter(Team.team_id == team_id).first()
        return team_obj

def get_teams_by_event(event_id: int, db: Session):
        teams = (
        db.query(Team)
        .join(RobotPerformance)
        .join(Match)
        .filter(Match.event_id == event_id)
        .distinct()
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