#!/usr/bin/env python3
"""
Monitor training progress and auto-deploy when complete
"""

import subprocess
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
TRAINING_SCRIPT_PID = None
NEW_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"


def check_training_complete():
    """Check if training process has finished."""
    try:
        result = subprocess.run(
            "ps aux | grep train_frc_detector_option_c | grep -v grep",
            shell=True,
            capture_output=True,
            text=True
        )
        return result.returncode != 0  # Training done if process not found
    except:
        return False


def check_model_exists():
    """Check if trained model exists."""
    return NEW_MODEL.exists()


def run_deployment():
    """Run deployment script."""
    print("\n" + "="*70)
    print("🚀 TRAINING COMPLETE - STARTING DEPLOYMENT")
    print("="*70)
    
    result = subprocess.run(
        ["python3", "deploy_model.py"],
        cwd=PROJECT_ROOT
    )
    
    return result.returncode == 0


def main():
    """Monitor and deploy."""
    print("\n" + "="*70)
    print("📊 MONITORING TRAINING PROGRESS")
    print("="*70)
    print(f"  Checking every 30 seconds for completion...")
    print(f"  Training PID: 19812")
    print()
    
    check_count = 0
    
    while True:
        check_count += 1
        
        if check_training_complete():
            print(f"\n✓ Training process finished!")
            
            # Wait a moment for file I/O
            time.sleep(2)
            
            if check_model_exists():
                print(f"✓ Model saved: {NEW_MODEL.name}")
                success = run_deployment()
                return 0 if success else 1
            else:
                print(f"❌ Model not found at: {NEW_MODEL}")
                return 1
        
        # Show progress dots
        elapsed_min = (check_count * 30) // 60
        print(f"  [{elapsed_min:2d}m] Training running... ", end='', flush=True)
        
        # Check CPU usage
        try:
            result = subprocess.run(
                "ps aux | grep train_frc_detector_option_c | grep -v grep | awk '{print $3}' | head -1",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            cpu = result.stdout.strip()
            print(f"CPU: {cpu}%")
        except:
            print("running")
        
        time.sleep(30)


if __name__ == "__main__":
    sys.exit(main())
