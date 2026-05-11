#!/usr/bin/env python3
"""Queue match 522273 for reprocessing with new model."""

import os
import sys
from pathlib import Path

# Setup environment
os.chdir(str(Path(__file__).parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Set environment variables
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@localhost/scouterfrc')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')

# Import after path setup
from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.match import Match
from app.models.alliance import Alliance
from app.tasks.video_tasks import process_video_file

def main():
    db = SessionLocal()
    try:
        match = db.query(Match).filter(Match.match_id == 522273).first()
        
        if not match:
            print(f"❌ Match 522273 not found")
            return
        
        # Get alliance teams
        alliances = db.query(Alliance).filter(Alliance.match_id == 522273).all()
        alliance_teams = {"red": [], "blue": []}
        for a in alliances:
            team_nums = [rp.team.team_number for rp in a.robot_performances]
            alliance_teams[a.color] = team_nums
        
        print(f"🎥 Queuing match {match.match_id} for processing")
        print(f"  Video: {match.video_url}")
        print(f"  Red teams: {alliance_teams['red']}")
        print(f"  Blue teams: {alliance_teams['blue']}")
        
        # Queue the task
        task = process_video_file.delay(
            match_id=match.match_id,
            video_url=match.video_url,
            alliance_teams=alliance_teams,
            event_id=match.event_id,
        )
        
        print(f"\n✓ Task queued!")
        print(f"  Task ID: {task.id}")
        print(f"  Status: PENDING")
        print(f"\n📊 Monitor progress:")
        print(f"  - Flower UI: http://localhost:5555/tasks/{task.id}")
        print(f"  - Once complete, visualize: http://localhost:5173/matches/522273/visualization")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
