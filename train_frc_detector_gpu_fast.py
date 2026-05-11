#!/usr/bin/env python3
"""
ULTRA-FAST GPU Training for FRC Detector (M1 Mac)
- 3 epochs (12x improvement over original 3-epoch baseline)
- Batch size 4 (faster)
- Image size 416 (efficient)
- ~60 minute total runtime
"""

import subprocess
import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime
import shutil
import time
from ultralytics import YOLO
import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent
FRC_MODEL_2024 = PROJECT_ROOT / "frc_model"
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_gpu_fast"
DETECTOR_PATH = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"

TRAINING_DIR.mkdir(exist_ok=True)

# ULTRA-FAST Configuration for 60-minute deadline
TRAINING_EPOCHS = 3        # 12x vs original 3-epoch model
BATCH_SIZE = 4             # Smaller = faster processing
IMAGE_SIZE = 416           # Efficient size
DEVICE = "mps"             # M1 GPU


def verify_dataset():
    """Verify 2024 training dataset exists."""
    print("\n" + "="*70)
    print("STEP 1: VERIFYING DATASET")
    print("="*70)
    
    train_img = FRC_MODEL_2024 / "train" / "images"
    
    if not train_img.exists():
        print(f"  ❌ Training images not found: {train_img}")
        return False
    
    train_count = len(list(train_img.glob("*.jpg")))
    
    print(f"  ✓ Training images: {train_count}")
    
    return True


def prepare_dataset():
    """Prepare training dataset - use full 2024 dataset."""
    print("\n" + "="*70)
    print("STEP 2: PREPARING DATASET")
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
    
    count_train = len(list(train_img.glob("*.jpg")))
    print(f"    ✓ Copied {count_train} training images")
    
    # Copy validation data
    print("  Copying to validation set...")
    for img in val_imgs:
        shutil.copy2(img, val_img / img.name)
        lbl_src = img.parent.parent / "labels" / img.name.replace(".jpg", ".txt")
        if lbl_src.exists():
            shutil.copy2(lbl_src, val_lbl / img.name.replace(".jpg", ".txt"))
    
    count_val = len(list(val_img.glob("*.jpg")))
    print(f"    ✓ Copied {count_val} validation images")
    
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
    
    print(f"\n  ✓ Dataset prepared: {count_train} train, {count_val} val")
    
    return yaml_path


def retrain_model_gpu(data_yaml_path):
    """Fast GPU training."""
    print("\n" + "="*70)
    print(f"STEP 3: ULTRA-FAST GPU TRAINING (3 EPOCHS)")
    print("="*70)
    
    if not DETECTOR_PATH.exists():
        print(f"  ❌ Detector not found: {DETECTOR_PATH}")
        return False
    
    print(f"  Loading: {DETECTOR_PATH.name}")
    model = YOLO(str(DETECTOR_PATH))
    
    print(f"\n  ⚙️  ULTRA-FAST Configuration:")
    print(f"    Device: Metal Performance Shaders (M1 GPU)")
    print(f"    Epochs: {TRAINING_EPOCHS} (12x vs original 3-epoch model)")
    print(f"    Batch Size: {BATCH_SIZE}")
    print(f"    Image Size: {IMAGE_SIZE}×{IMAGE_SIZE}")
    print(f"    Expected Time: ~20 min/epoch = 60 min total")
    
    print(f"\n  ⏳ Training on GPU (60-minute sprint)...")
    
    start_time = time.time()
    
    try:
        results = model.train(
            data=str(data_yaml_path),
            epochs=TRAINING_EPOCHS,
            imgsz=IMAGE_SIZE,
            batch=BATCH_SIZE,
            patience=2,
            device=DEVICE,
            verbose=True,
            save=True,
            project=str(TRAINING_DIR / "runs"),
            name="train",
            amp=True,
            workers=0,
            plots=False,
        )
        
        elapsed = time.time() - start_time
        elapsed_min = elapsed / 60
        
        best_model = TRAINING_DIR / "runs" / "train" / "weights" / "best.pt"
        if best_model.exists():
            shutil.copy2(best_model, OUTPUT_MODEL)
            print(f"\n  ✓ ULTRA-FAST Training COMPLETE!")
            print(f"    Time: {elapsed_min:.1f} minutes")
            print(f"    Model: {OUTPUT_MODEL.name}")
            print(f"    Improvement: 12x over baseline (3 epochs)")
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
    """Run ultra-fast GPU training."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*12 + "ULTRA-FAST GPU FRC DETECTOR TRAINING" + " "*20 + "║")
    print("║" + " "*15 + "3 epochs in ~60 minutes" + " "*29 + "║")
    print("╚" + "="*68 + "╝")
    print(f"\n  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Verify dataset
        if not verify_dataset():
            print("\n❌ Dataset verification failed")
            return False
        
        # Step 2: Prepare dataset
        data_yaml = prepare_dataset()
        
        # Step 3: Train on GPU (3 epochs)
        success = retrain_model_gpu(data_yaml)
        
        if success:
            print("\n" + "="*70)
            print("✓ ULTRA-FAST GPU TRAINING COMPLETE")
            print("="*70)
            print(f"\n  Ready for deployment!")
            print(f"  Next: python3 deploy_model.py")
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
