#!/usr/bin/env python3
"""
Deploy retrained FRC detector and validate improvements
- Checks for frc_robot_detector_v2.pt
- Deploys to Docker
- Reprocesses test match 522273
- Validates detection improvements
"""

import subprocess
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent
OLD_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
NEW_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"
DOCKER_COMPOSE = PROJECT_ROOT / "docker-compose.yml"

TEST_MATCH_ID = 522273


def check_model_exists():
    """Check if new model has been trained."""
    if not NEW_MODEL.exists():
        print(f"❌ New model not found: {NEW_MODEL}")
        print(f"   Wait for training to complete first")
        return False
    
    old_size = OLD_MODEL.stat().st_size / 1024 / 1024
    new_size = NEW_MODEL.stat().st_size / 1024 / 1024
    
    print(f"✓ Models ready for deployment:")
    print(f"  Current: {OLD_MODEL.name} ({old_size:.1f} MB)")
    print(f"  New:     {NEW_MODEL.name} ({new_size:.1f} MB)")
    
    return True


def deploy_model():
    """Deploy new model by replacing old one."""
    print(f"\n{'='*70}")
    print("DEPLOYING NEW MODEL")
    print(f"{'='*70}")
    
    import shutil
    
    print(f"  Backing up current model...")
    backup = OLD_MODEL.with_suffix('.pt.backup')
    if backup.exists():
        backup.unlink()
    shutil.copy2(OLD_MODEL, backup)
    print(f"    ✓ Backup: {backup.name}")
    
    print(f"  Deploying new model...")
    shutil.copy2(NEW_MODEL, OLD_MODEL)
    print(f"    ✓ Deployed: {OLD_MODEL.name}")
    
    return True


def restart_docker():
    """Restart Docker services."""
    print(f"\n{'='*70}")
    print("RESTARTING DOCKER SERVICES")
    print(f"{'='*70}")
    
    print(f"  Restarting containers...")
    result = subprocess.run(
        ["docker-compose", "restart", "celery_worker", "backend"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Docker restart failed: {result.stderr}")
        return False
    
    print(f"    ✓ Containers restarted")
    
    # Wait for services to be ready
    print(f"  Waiting for services to be ready...")
    time.sleep(5)
    
    return True


def queue_test_match():
    """Queue test match for reprocessing."""
    print(f"\n{'='*70}")
    print(f"TESTING WITH MATCH {TEST_MATCH_ID}")
    print(f"{'='*70}")
    
    print(f"  Queueing match {TEST_MATCH_ID} for processing...")
    
    result = subprocess.run(
        [
            "docker-compose", "exec", "backend", "bash", "-c",
            f"cd /app && python -c \"from app.tasks.auto_video_tasks import process_match_video_from_url; task = process_match_video_from_url.delay({TEST_MATCH_ID}); print(f'✓ Task queued: {{task.id}})')\""
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and "Task queued" in result.stdout:
        print(f"    ✓ {result.stdout.strip()}")
        return True
    else:
        print(f"    ❌ Failed to queue match: {result.stderr}")
        return False


def show_next_steps():
    """Show deployment complete message."""
    print(f"\n{'='*70}")
    print("✓ DEPLOYMENT COMPLETE")
    print(f"{'='*70}")
    
    print(f"\n  ✅ New model deployed: frc_robot_detector_v2.pt")
    print(f"  ✅ Docker services restarted")
    print(f"  ✅ Match {TEST_MATCH_ID} queued for reprocessing")
    
    print(f"\n  Next steps:")
    print(f"    1. Wait 5-10 minutes for match reprocessing")
    print(f"    2. Visit visualization:")
    print(f"       http://localhost:5173/matches/{TEST_MATCH_ID}/visualization")
    print(f"    3. Compare detection quality (should see more/better tracks)")
    
    print(f"\n  To monitor processing:")
    print(f"    docker-compose logs celery_worker 2>&1 | tail -50")
    
    print(f"\n  To check match status:")
    print(f"    docker-compose exec postgres psql -U postgres -d scouterfrc -c \\")
    print(f"      \"SELECT COUNT(*) FROM movement_track WHERE match_id = {TEST_MATCH_ID}\"")
    print()


def main():
    """Run deployment pipeline."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*20 + "MODEL DEPLOYMENT PIPELINE" + " "*24 + "║")
    print("╚" + "="*68 + "╝")
    
    # Step 1: Check model
    if not check_model_exists():
        return False
    
    # Step 2: Deploy
    if not deploy_model():
        return False
    
    # Step 3: Restart Docker
    if not restart_docker():
        print("⚠️  Docker restart may have failed. Try manual restart:")
        print("    docker-compose restart celery_worker backend")
        return False
    
    # Step 4: Queue test
    if not queue_test_match():
        print("⚠️  Could not queue test match. Try manual queue:")
        print(f"    docker-compose exec backend bash -c \"cd /app && python -c")
        print(f"      \\\"from app.tasks.auto_video_tasks import process_match_video_from_url;")
        print(f"      process_match_video_from_url.delay({TEST_MATCH_ID})\\\"\"")
        return False
    
    # Step 5: Show next steps
    show_next_steps()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
