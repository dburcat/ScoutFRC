#!/usr/bin/env python3
"""
Monitor FRC detector training progress
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_enhanced"
BEST_MODEL = TRAINING_DIR / "runs" / "train" / "weights" / "best.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"


def check_training_status():
    """Check if training is still running."""
    # Try to connect to Python training process
    result = subprocess.run(
        ["pgrep", "-f", "train_frc_detector_simple.py"],
        capture_output=True
    )
    
    return result.returncode == 0  # 0 = process found


def get_training_progress():
    """Get training progress from ultralytics runs."""
    results_csv = TRAINING_DIR / "runs" / "train" / "results.csv"
    
    if not results_csv.exists():
        return None, None
    
    try:
        import csv
        with open(results_csv, 'r') as f:
            reader = list(csv.DictReader(f))
            if reader:
                last = reader[-1]
                epoch = len(reader)
                
                return epoch, last
        
    except Exception as e:
        print(f"  Error reading results: {e}")
    
    return None, None


def main():
    """Monitor training."""
    print("\n" + "="*70)
    print("FRC DETECTOR TRAINING MONITOR")
    print("="*70)
    
    # Check if training is running
    is_running = check_training_status()
    
    print(f"\n  Status: {'🟢 TRAINING IN PROGRESS' if is_running else '🔴 TRAINING NOT RUNNING'}")
    print(f"  Directory: {TRAINING_DIR}")
    print(f"  Start time: Check 'date' when process started")
    
    # Get progress
    epoch, metrics = get_training_progress()
    
    if epoch:
        print(f"\n  Progress: Epoch {epoch} / 75 ({epoch/75*100:.0f}%)")
        
        if metrics:
            print(f"\n  Latest metrics (Epoch {epoch}):")
            
            # Show key metrics if available
            key_metrics = ['box_loss', 'cls_loss', 'dfl_loss', 'val/box_loss', 'metrics/precision(B)', 'metrics/recall(B)', 'metrics/mAP50(B)']
            
            for metric in key_metrics:
                if metric in metrics and metrics[metric]:
                    try:
                        val = float(metrics[metric])
                        print(f"    {metric}: {val:.4f}")
                    except:
                        pass
    else:
        print(f"\n  ⏳ Training metrics not yet available...")
    
    # Check for best model
    if BEST_MODEL.exists():
        size = BEST_MODEL.stat().st_size / 1024 / 1024
        print(f"\n  Best model saved: {BEST_MODEL.name} ({size:.1f} MB)")
    
    if OUTPUT_MODEL.exists():
        size = OUTPUT_MODEL.stat().st_size / 1024 / 1024
        print(f"  ✓ Final model ready: {OUTPUT_MODEL.name} ({size:.1f} MB)")
        print(f"\n  🎉 Training complete! Run: python3 deploy_model.py")
    
    print()


if __name__ == "__main__":
    main()
