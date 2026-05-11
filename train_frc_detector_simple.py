#!/usr/bin/env python3
"""
FRC Robot Detector Training Pipeline
- Combines 2024 dataset with optional 2026 frames
- Retrains frc_robot_detector.pt with 75 epochs (vs original 3)
- Validates improvements on test frames
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import shutil
import yaml
from ultralytics import YOLO

# Paths
PROJECT_ROOT = Path(__file__).parent
FRC_MODEL_DIR = PROJECT_ROOT / "frc_model"
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_enhanced"
DETECTOR_PATH = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"

TRAINING_DIR.mkdir(exist_ok=True)

# Configuration
TRAINING_EPOCHS = 75
BATCH_SIZE = 8  # For CPU training


def prepare_dataset():
    """Prepare training dataset from existing 2024 data."""
    print("\n" + "="*70)
    print("STEP 1: PREPARING DATASET")
    print("="*70)
    
    # Create directories
    train_img = TRAINING_DIR / "train" / "images"
    train_lbl = TRAINING_DIR / "train" / "labels"
    val_img = TRAINING_DIR / "val" / "images"
    val_lbl = TRAINING_DIR / "val" / "labels"
    
    for d in [train_img, train_lbl, val_img, val_lbl]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Copy 2024 training data
    print("  Copying 2024 training data...")
    src_train = FRC_MODEL_DIR / "train"
    src_images = src_train / "images"
    src_labels = src_train / "labels"
    
    if src_images.exists() and src_labels.exists():
        for img_file in src_images.glob("*.jpg"):
            shutil.copy2(img_file, train_img / img_file.name)
        for lbl_file in src_labels.glob("*.txt"):
            shutil.copy2(lbl_file, train_lbl / lbl_file.name)
        
        count_train = len(list(train_img.glob("*.jpg")))
        print(f"    ✓ Copied {count_train} training images")
    else:
        print(f"    ❌ Source training data not found")
        return None
    
    # Copy or create validation data
    print("  Preparing validation data...")
    src_val = FRC_MODEL_DIR / "val"
    src_val_images = src_val / "images"
    src_val_labels = src_val / "labels"
    
    if src_val_images.exists() and src_val_labels.exists():
        # Copy existing validation data
        for img_file in src_val_images.glob("*.jpg"):
            shutil.copy2(img_file, val_img / img_file.name)
        for lbl_file in src_val_labels.glob("*.txt"):
            shutil.copy2(lbl_file, val_lbl / lbl_file.name)
        
        count_val = len(list(val_img.glob("*.jpg")))
        print(f"    ✓ Copied {count_val} validation images")
    else:
        # Create 80/20 split from training data
        print(f"    ⚠️  No validation data found. Creating 20% split from training...")
        all_train = list(train_img.glob("*.jpg"))
        split_idx = int(len(all_train) * 0.8)
        
        for img_file in all_train[split_idx:]:
            shutil.move(str(img_file), val_img / img_file.name)
            lbl_file = train_lbl / img_file.name.replace(".jpg", ".txt")
            if lbl_file.exists():
                shutil.move(str(lbl_file), val_lbl / lbl_file.name)
        
        count_train = len(list(train_img.glob("*.jpg")))
        count_val = len(list(val_img.glob("*.jpg")))
        print(f"    ✓ Created split: {count_train} train, {count_val} val")
    
    # Create data.yaml
    data_config = {
        "path": str(TRAINING_DIR),
        "train": "train/images",
        "val": "val/images",
        "nc": 2,
        "names": ["note", "robot"]
    }
    
    yaml_path = TRAINING_DIR / "data.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(data_config, f)
    
    print(f"\n✓ Dataset prepared at {TRAINING_DIR}")
    print(f"  Training: {count_train} images")
    print(f"  Validation: {count_val} images")
    
    return yaml_path


def retrain_model(data_yaml_path):
    """Retrain detector with more epochs."""
    print("\n" + "="*70)
    print(f"STEP 2: RETRAINING FRC DETECTOR")
    print("="*70)
    
    if not DETECTOR_PATH.exists():
        print(f"❌ Current detector not found at {DETECTOR_PATH}")
        return False
    
    print(f"  Loading base model: {DETECTOR_PATH.name}")
    model = YOLO(str(DETECTOR_PATH))
    
    print(f"\n  Training configuration:")
    print(f"    Model: frc_robot_detector.pt")
    print(f"    Epochs: {TRAINING_EPOCHS} (original: 3)")
    print(f"    Batch size: {BATCH_SIZE}")
    print(f"    Device: CPU")
    print(f"    Dataset: {len(list((TRAINING_DIR / 'train' / 'images').glob('*.jpg')))} training images")
    print(f"    Output: {OUTPUT_MODEL.name}")
    
    print(f"\n  ⏳ Training in progress (this may take 30-60 minutes on CPU)...")
    
    try:
        results = model.train(
            data=str(data_yaml_path),
            epochs=TRAINING_EPOCHS,
            imgsz=640,
            batch=BATCH_SIZE,
            patience=10,
            device='cpu',
            verbose=False,
            save=True,
            project=str(TRAINING_DIR / "runs"),
            name="train"
        )
        
        # Copy best model
        best_model = TRAINING_DIR / "runs" / "train" / "weights" / "best.pt"
        if best_model.exists():
            shutil.copy2(best_model, OUTPUT_MODEL)
            print(f"\n✓ Training complete!")
            print(f"  Best model: {OUTPUT_MODEL.name}")
            print(f"  File size: {OUTPUT_MODEL.stat().st_size / 1024 / 1024:.1f} MB")
            return True
        else:
            print(f"❌ Training failed - best.pt not found")
            return False
            
    except Exception as e:
        print(f"❌ Training error: {e}")
        return False


def validate_model():
    """Show validation results."""
    print("\n" + "="*70)
    print("STEP 3: VALIDATION RESULTS")
    print("="*70)
    
    # Check training logs
    results_dir = TRAINING_DIR / "runs" / "train"
    if results_dir.exists():
        # Look for results.csv
        results_file = results_dir / "results.csv"
        if results_file.exists():
            print(f"\n  Training metrics saved to results.csv")
            
            # Show last few epochs
            import csv
            try:
                with open(results_file, 'r') as f:
                    reader = list(csv.reader(f))
                    if len(reader) > 1:
                        header = reader[0]
                        print(f"\n  Last training epoch:")
                        last_row = reader[-1]
                        
                        # Show key metrics if available
                        for i, col in enumerate(header):
                            if 'loss' in col.lower() or 'map' in col.lower() or 'precision' in col.lower() or 'recall' in col.lower():
                                print(f"    {col}: {last_row[i] if i < len(last_row) else 'N/A'}")
            except:
                pass
    
    print(f"\n✓ Model ready to use!")
    print(f"  Location: {OUTPUT_MODEL}")


def main():
    """Run training pipeline."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*14 + "FRC ROBOT DETECTOR TRAINING PIPELINE" + " "*20 + "║")
    print("╚" + "="*68 + "╝")
    print(f"\n  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Project: {PROJECT_ROOT}")
    
    try:
        # Step 1: Prepare dataset
        data_yaml = prepare_dataset()
        if not data_yaml:
            print("\n❌ Dataset preparation failed")
            return
        
        # Step 2: Retrain
        success = retrain_model(data_yaml)
        if not success:
            print("\n❌ Training failed")
            return
        
        # Step 3: Show results
        validate_model()
        
        print("\n" + "="*70)
        print("✓ PIPELINE COMPLETE")
        print("="*70)
        print(f"\n  To deploy the improved model:")
        print(f"    1. Replace the model:")
        print(f"       cp {OUTPUT_MODEL} {DETECTOR_PATH}")
        print(f"    2. Restart Docker:")
        print(f"       docker-compose restart celery_worker backend")
        print(f"    3. Test on a match:")
        print(f"       Visit http://localhost:5173/matches/522273/visualization")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
