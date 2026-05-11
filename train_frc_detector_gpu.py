#!/usr/bin/env python3
"""
GPU-Optimized FRC Detector Training (M1 Mac with Metal Performance Shaders)
- Retrains frc_robot_detector.pt with 75 epochs on GPU
- Uses Metal Performance Shaders (MPS) for M1 acceleration
- 25x more training (3 epochs → 75 epochs)
- ~2-3 hours instead of 50 hours
"""

import subprocess
import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime
import shutil
import cv2
import numpy as np
from ultralytics import YOLO
import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent
FRC_MODEL_2024 = PROJECT_ROOT / "frc_model"
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_gpu"
DETECTOR_PATH = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"

TRAINING_DIR.mkdir(exist_ok=True)

# Configuration
TRAINING_EPOCHS = 75
BATCH_SIZE = 16  # Larger batch size on GPU
DEVICE = "mps"  # M1 GPU via Metal Performance Shaders


def verify_dataset():
    """Verify 2024 training dataset exists."""
    print("\n" + "="*70)
    print("STEP 1: VERIFYING DATASET")
    print("="*70)
    
    train_img = FRC_MODEL_2024 / "train" / "images"
    val_img = FRC_MODEL_2024 / "val" / "images"
    
    if not train_img.exists():
        print(f"  ❌ Training images not found: {train_img}")
        return False
    
    train_count = len(list(train_img.glob("*.jpg")))
    val_count = len(list(val_img.glob("*.jpg"))) if val_img.exists() else 0
    
    print(f"  ✓ Training images: {train_count}")
    print(f"  ✓ Validation images: {val_count}")
    print(f"  ✓ Total: {train_count + val_count} images")
    
    if train_count < 100:
        print(f"  ⚠️  Warning: Small dataset ({train_count} images)")
    
    return True


def prepare_dataset():
    """Prepare training dataset."""
    print("\n" + "="*70)
    print("STEP 2: PREPARING DATASET FOR TRAINING")
    print("="*70)
    
    train_img = TRAINING_DIR / "train" / "images"
    train_lbl = TRAINING_DIR / "train" / "labels"
    val_img = TRAINING_DIR / "val" / "images"
    val_lbl = TRAINING_DIR / "val" / "labels"
    
    for d in [train_img, train_lbl, val_img, val_lbl]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Collect all images
    print("  Collecting all 2024 images...")
    src_2024_train = FRC_MODEL_2024 / "train"
    src_2024_val = FRC_MODEL_2024 / "val"
    
    all_imgs = []
    all_imgs.extend((src_2024_train / "images").glob("*.jpg"))
    if (src_2024_val / "images").exists():
        all_imgs.extend((src_2024_val / "images").glob("*.jpg"))
    
    print(f"    Found {len(all_imgs)} total images")
    
    # Create 80/20 train/val split
    import random
    random.shuffle(all_imgs)
    split_idx = int(len(all_imgs) * 0.8)
    
    train_imgs = all_imgs[:split_idx]
    val_imgs = all_imgs[split_idx:]
    
    # Copy training data
    print("  Copying to training set...")
    for img in train_imgs:
        shutil.copy2(img, train_img / img.name)
        lbl_src = img.parent.parent / "labels" / img.name.replace(".jpg", ".txt")
        if lbl_src.exists():
            shutil.copy2(lbl_src, train_lbl / img.name.replace(".jpg", ".txt"))
    
    count_2024_train = len(list(train_img.glob("*.jpg")))
    print(f"    ✓ Copied {count_2024_train} training images")
    
    # Copy validation data
    print("  Copying to validation set...")
    for img in val_imgs:
        shutil.copy2(img, val_img / img.name)
        lbl_src = img.parent.parent / "labels" / img.name.replace(".jpg", ".txt")
        if lbl_src.exists():
            shutil.copy2(lbl_src, val_lbl / img.name.replace(".jpg", ".txt"))
    
    count_2024_val = len(list(val_img.glob("*.jpg")))
    print(f"    ✓ Copied {count_2024_val} validation images")
    
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
    
    print(f"\n  ✓ Dataset prepared:")
    print(f"    Train: {count_2024_train} images")
    print(f"    Val:   {count_2024_val} images")
    
    return yaml_path


def retrain_model_gpu(data_yaml_path):
    """Retrain model on GPU."""
    print("\n" + "="*70)
    print(f"STEP 3: GPU TRAINING WITH 75 EPOCHS")
    print("="*70)
    
    if not DETECTOR_PATH.exists():
        print(f"  ❌ Detector not found: {DETECTOR_PATH}")
        return False
    
    print(f"  Loading: {DETECTOR_PATH.name}")
    model = YOLO(str(DETECTOR_PATH))
    
    print(f"\n  Configuration:")
    print(f"    Device: Metal Performance Shaders (M1 GPU)")
    print(f"    Epochs: {TRAINING_EPOCHS} (original: 3 = 25x improvement)")
    print(f"    Batch: {BATCH_SIZE} (GPU-optimized)")
    print(f"    Image size: 640")
    print(f"    Dataset: {TRAINING_DIR}")
    
    print(f"\n  ⏳ Training on GPU (2-3 hours)...")
    print(f"     GPU acceleration will make this MUCH faster than CPU!")
    
    try:
        results = model.train(
            data=str(data_yaml_path),
            epochs=TRAINING_EPOCHS,
            imgsz=640,
            batch=BATCH_SIZE,
            patience=10,
            device=DEVICE,  # Use GPU
            verbose=False,
            save=True,
            project=str(TRAINING_DIR / "runs"),
            name="train",
            amp=True  # Automatic Mixed Precision for faster GPU training
        )
        
        best_model = TRAINING_DIR / "runs" / "train" / "weights" / "best.pt"
        if best_model.exists():
            shutil.copy2(best_model, OUTPUT_MODEL)
            print(f"\n  ✓ GPU Training complete!")
            print(f"    Model: {OUTPUT_MODEL.name}")
            print(f"    Size: {OUTPUT_MODEL.stat().st_size / 1024 / 1024:.1f} MB")
            return True
        else:
            print(f"  ❌ Training failed - best.pt not found")
            return False
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run GPU training pipeline."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*12 + "GPU-OPTIMIZED FRC DETECTOR TRAINING" + " "*22 + "║")
    print("║" + " "*10 + "M1 Mac Metal Performance Shaders (2-3 hours)" + " "*14 + "║")
    print("╚" + "="*68 + "╝")
    print(f"\n  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Verify dataset
        if not verify_dataset():
            print("\n❌ Dataset verification failed")
            return False
        
        # Step 2: Prepare dataset
        data_yaml = prepare_dataset()
        
        # Step 3: Train on GPU
        success = retrain_model_gpu(data_yaml)
        
        if success:
            print("\n" + "="*70)
            print("✓ GPU TRAINING COMPLETE - MODEL READY FOR DEPLOYMENT")
            print("="*70)
            print(f"\n  Next: python3 deploy_model.py")
            print()
            return True
        else:
            print("\n❌ Training failed")
            return False
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted")
        return False
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
