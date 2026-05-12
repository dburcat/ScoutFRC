#!/usr/bin/env python3
"""
Improved FRC Detector Training with Better Configuration
- Uses yolov8m (medium model) instead of nano for better accuracy
- Increased epochs (150) for convergence
- Enhanced data augmentation
- Higher confidence threshold to reduce false positives
- Larger batch size for stable gradients
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
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_gpu_improved"
DETECTOR_PATH = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_improved.pt"

TRAINING_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# IMPROVED CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Model configuration
MODEL_SIZE = "m"  # "m" (medium) instead of "n" (nano) for better accuracy
TRAINING_EPOCHS = 150  # Increased from 75
BATCH_SIZE = 32  # Larger batch for stable gradients
PATIENCE = 30  # Early stopping patience
IMG_SIZE = 640

# Device selection
def select_device():
    """Select best available device."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"  # M1/M2 Mac
        else:
            return "cpu"
    except:
        return "cpu"

DEVICE = select_device()

# Detection parameters
CONFIDENCE_THRESHOLD = 0.50  # Increased from 0.20 to reduce false positives
IOU_THRESHOLD = 0.50  # Increased from 0.45 to reduce duplicate detections


def verify_dataset():
    """Verify 2024 training dataset exists and is valid."""
    print("\n" + "="*70)
    print("STEP 1: VERIFYING DATASET")
    print("="*70)
    
    train_img = FRC_MODEL_2024 / "train" / "images"
    train_lbl = FRC_MODEL_2024 / "train" / "labels"
    val_img = FRC_MODEL_2024 / "val" / "images"
    val_lbl = FRC_MODEL_2024 / "val" / "labels"
    
    if not train_img.exists():
        print(f"  ❌ Training images not found: {train_img}")
        return False
    
    train_count = len(list(train_img.glob("*.jpg"))) + len(list(train_img.glob("*.png")))
    val_count = len(list(val_img.glob("*.jpg"))) + len(list(val_img.glob("*.png"))) if val_img.exists() else 0
    train_lbl_count = len(list(train_lbl.glob("*.txt"))) if train_lbl.exists() else 0
    
    print(f"  ✓ Training images: {train_count}")
    print(f"  ✓ Training labels: {train_lbl_count}")
    print(f"  ✓ Validation images: {val_count}")
    
    if train_count < 200:
        print(f"  ⚠️  Warning: Small dataset ({train_count} images). Better with 500+")
    
    if train_lbl_count == 0:
        print(f"  ❌ ERROR: No training labels found!")
        return False
    
    print(f"  ✓ Label/Image ratio: {train_lbl_count}/{train_count}")
    
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
        # Clear any existing files
        for f in d.glob("*"):
            f.unlink()
    
    # Collect all images
    print("  Collecting all training images...")
    src_train = FRC_MODEL_2024 / "train"
    src_val = FRC_MODEL_2024 / "val"
    
    all_imgs = []
    all_imgs.extend((src_train / "images").glob("*.jpg"))
    all_imgs.extend((src_train / "images").glob("*.png"))
    if (src_val / "images").exists():
        all_imgs.extend((src_val / "images").glob("*.jpg"))
        all_imgs.extend((src_val / "images").glob("*.png"))
    
    print(f"    Found {len(all_imgs)} total images")
    
    # Create 80/20 train/val split
    random.shuffle(all_imgs)
    split_idx = int(len(all_imgs) * 0.8)
    
    train_imgs = all_imgs[:split_idx]
    val_imgs = all_imgs[split_idx:]
    
    # Copy training data with labels
    print("  Copying to training set...")
    for img in train_imgs:
        shutil.copy2(img, train_img / img.name)
        # Find corresponding label
        lbl_src = img.parent.parent / "labels" / img.name.replace(".jpg", ".txt").replace(".png", ".txt")
        if lbl_src.exists():
            shutil.copy2(lbl_src, train_lbl / img.name.replace(".jpg", ".txt").replace(".png", ".txt"))
    
    count_train = len(list(train_img.glob("*")))
    print(f"    ✓ Copied {count_train} training images")
    
    # Copy validation data with labels
    print("  Copying to validation set...")
    for img in val_imgs:
        shutil.copy2(img, val_img / img.name)
        lbl_src = img.parent.parent / "labels" / img.name.replace(".jpg", ".txt").replace(".png", ".txt")
        if lbl_src.exists():
            shutil.copy2(lbl_src, val_lbl / img.name.replace(".jpg", ".txt").replace(".png", ".txt"))
    
    count_val = len(list(val_img.glob("*")))
    print(f"    ✓ Copied {count_val} validation images")
    
    # Detect number of classes from label files
    num_classes = 0
    class_set = set()
    sample_label = next(train_lbl.glob("*.txt"), None)
    if sample_label:
        with open(sample_label) as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    class_set.add(int(parts[0]))
    
    num_classes = len(class_set)
    if num_classes == 0:
        print(f"  ⚠️  WARNING: Could not determine class count, assuming 1 (robot only)")
        num_classes = 1
    
    class_names = {0: "robot"} if num_classes == 1 else {0: "note", 1: "robot"}
    
    print(f"  ✓ Detected {num_classes} class(es): {list(class_names.values())}")
    
    # Create data.yaml
    data_config = {
        "path": str(TRAINING_DIR),
        "train": "train/images",
        "val": "val/images",
        "nc": num_classes,
        "names": [class_names[i] for i in range(num_classes)]
    }
    
    yaml_path = TRAINING_DIR / "data.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(data_config, f)
    
    print(f"\n  ✓ Dataset prepared:")
    print(f"    Train: {count_train} images")
    print(f"    Val:   {count_val} images")
    print(f"    Total: {count_train + count_val} images")
    print(f"    Classes: {num_classes} ({', '.join(class_names.values())})")
    
    return yaml_path


def train_model_improved(data_yaml_path):
    """Train model with improved configuration."""
    print("\n" + "="*70)
    print(f"STEP 3: IMPROVED TRAINING")
    print(f"  Model: yolov8{MODEL_SIZE}")
    print(f"  Epochs: {TRAINING_EPOCHS}")
    print(f"  Batch: {BATCH_SIZE}")
    print(f"  Device: {DEVICE}")
    print(f"  Confidence: {CONFIDENCE_THRESHOLD}")
    print("="*70)
    
    print(f"\n  Loading base model: yolov8{MODEL_SIZE}.pt")
    model = YOLO(f"yolov8{MODEL_SIZE}.pt")
    model.to(DEVICE)
    
    print(f"  Starting training with improved config...")
    print(f"  Epochs: {TRAINING_EPOCHS}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Image size: {IMG_SIZE}x{IMG_SIZE}")
    
    results = model.train(
        data=str(data_yaml_path),
        epochs=TRAINING_EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=DEVICE,
        patience=PATIENCE,
        save=True,
        
        # ─────────────────────────────────────────────────────────────────
        # ENHANCED AUGMENTATION (reduces overfitting, improves robustness)
        # ─────────────────────────────────────────────────────────────────
        hsv_h=0.015,     # HSV-Hue augmentation
        hsv_s=0.7,       # HSV-Saturation augmentation
        hsv_v=0.4,       # HSV-Value augmentation
        degrees=10,      # Rotation ±10°
        translate=0.1,   # Translation 10%
        scale=0.5,       # Scale 0.5-1.5x
        flipud=0.5,      # Flip up-down 50%
        fliplr=0.5,      # Flip left-right 50%
        mosaic=1.0,      # Mosaic augmentation
        
        # ─────────────────────────────────────────────────────────────────
        # OPTIMIZATION
        # ─────────────────────────────────────────────────────────────────
        optimizer="SGD",
        lr0=0.01,        # Initial learning rate
        lrf=0.01,        # Final learning rate (at last epoch)
        momentum=0.937,
        weight_decay=0.0005,
        
        # ─────────────────────────────────────────────────────────────────
        # VALIDATION & CHECKPOINTING
        # ─────────────────────────────────────────────────────────────────
        val=True,
        save_period=10,
        project=str(TRAINING_DIR / "runs"),
        name="train_improved",
        exist_ok=False,
    )
    
    print(f"\n  ✓ Training complete")
    
    if results and hasattr(results, 'save_dir'):
        best_model_path = Path(results.save_dir) / "weights" / "best.pt"
        if best_model_path.exists():
            print(f"  ✓ Best model: {best_model_path}")
            print(f"  ✓ Model size: {best_model_path.stat().st_size / 1e6:.1f} MB")
            return best_model_path
    
    return None


def evaluate_model(model_path):
    """Evaluate trained model."""
    print("\n" + "="*70)
    print("STEP 4: MODEL EVALUATION")
    print("="*70)
    
    if not model_path or not model_path.exists():
        print(f"  ❌ Model not found: {model_path}")
        return False
    
    print(f"  Loading model: {model_path.name}")
    model = YOLO(str(model_path))
    
    # Validate on validation set
    val_dir = TRAINING_DIR / "val" / "images"
    if val_dir.exists() and list(val_dir.glob("*")):
        print(f"  Running validation on {len(list(val_dir.glob('*')))} images...")
        metrics = model.val(device=DEVICE)
        
        if metrics:
            print(f"\n  ✓ Validation Metrics:")
            print(f"    mAP50: {getattr(metrics, 'box.map50', 'N/A')}")
            print(f"    mAP50-95: {getattr(metrics, 'box.map', 'N/A')}")
    
    return True


def save_model(best_model_path):
    """Save model to final location."""
    print("\n" + "="*70)
    print("STEP 5: SAVING MODEL")
    print("="*70)
    
    if not best_model_path or not best_model_path.exists():
        print(f"  ❌ Best model not found")
        return False
    
    print(f"  Copying to: {OUTPUT_MODEL}")
    shutil.copy2(best_model_path, OUTPUT_MODEL)
    
    print(f"  ✓ Model saved")
    print(f"  ✓ Size: {OUTPUT_MODEL.stat().st_size / 1e6:.1f} MB")
    print(f"  ✓ Location: {OUTPUT_MODEL}")
    
    return True


def main():
    print("\n" + "="*70)
    print("FRC ROBOT DETECTOR - IMPROVED TRAINING")
    print(f"Version: yolov8{MODEL_SIZE} with Enhanced Config")
    print("="*70)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Training dir: {TRAINING_DIR}")
    print(f"Device: {DEVICE}")
    
    try:
        # Step 1: Verify dataset
        if not verify_dataset():
            print("\n❌ Dataset verification failed")
            return False
        
        # Step 2: Prepare dataset
        yaml_path = prepare_dataset()
        
        # Step 3: Train model
        best_model = train_model_improved(yaml_path)
        if not best_model:
            print("\n❌ Training failed")
            return False
        
        # Step 4: Evaluate model
        if not evaluate_model(best_model):
            print("\n⚠️  Evaluation failed, continuing anyway...")
        
        # Step 5: Save model
        if not save_model(best_model):
            print("\n❌ Model save failed")
            return False
        
        print("\n" + "="*70)
        print("✓ TRAINING COMPLETE")
        print("="*70)
        print(f"Model ready at: {OUTPUT_MODEL}")
        print(f"\nNext steps:")
        print(f"1. Transfer model back to main computer")
        print(f"2. Test with: python test_trained_model.py --video path/to/match.mp4")
        print(f"3. Deploy with docker compose up")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Training failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
