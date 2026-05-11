#!/usr/bin/env python3
"""
FRC Robot Detector Training Pipeline
- Collects 2026 match videos
- Extracts frames and creates annotations
- Combines with existing 2024 dataset
- Retrains frc_robot_detector.pt with more epochs
- Validates on test matches
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import shutil
import cv2
import numpy as np
from ultralytics import YOLO
import yt_dlp

# Paths
PROJECT_ROOT = Path(__file__).parent
FRC_MODEL_DIR = PROJECT_ROOT / "frc_model"
FRC_2024_DIR = PROJECT_ROOT / "FRC-2024-1"
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_enhanced"
FRAMES_CACHE = PROJECT_ROOT / ".frames_cache"
DETECTOR_PATH = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"

TRAINING_DIR.mkdir(exist_ok=True)
FRAMES_CACHE.mkdir(exist_ok=True)

# Configuration
MATCHES_TO_COLLECT = 5  # Number of 2026 matches to use for training data
FRAMES_PER_VIDEO = 30   # Extract N frames per video
TRAINING_EPOCHS = 75    # More than original 3 epochs
CONFIDENCE_THRESHOLD = 0.3


def download_match_videos():
    """Download videos for 2026 matches from database."""
    print("\n" + "="*70)
    print("STEP 1: DOWNLOADING 2026 MATCH VIDEOS")
    print("="*70)
    
    # Connect to database and get 2026 match URLs
    import os
    os.chdir(PROJECT_ROOT / "backend")
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))
    
    try:
        from app.db.database import SessionLocal
        from app.models import Match, Event
        
        db = SessionLocal()
        matches = db.query(Match).join(Event).filter(
            Event.season_year == 2026,
            Match.video_url.isnot(None)
        ).limit(MATCHES_TO_COLLECT).all()
        
        db.close()
        
        if not matches:
            print("❌ No 2026 matches with video URLs found in database")
            return []
        
        print(f"✓ Found {len(matches)} 2026 matches to download")
        
        videos = []
        for match in matches:
            match_id = match.match_id
            url = match.video_url
            video_path = FRAMES_CACHE / f"match_{match_id}.mp4"
            
            if video_path.exists():
                print(f"  ⟳ Match {match_id}: Already downloaded ({video_path.stat().st_size/1024/1024:.1f}MB)")
                videos.append((match_id, video_path))
            else:
                print(f"  ⏳ Match {match_id}: Downloading from {url[:60]}...")
                try:
                    ydl_opts = {
                        'format': 'best[ext=mp4]',
                        'quiet': True,
                        'no_warnings': True,
                        'outtmpl': str(video_path.with_suffix('')),
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    
                    if video_path.exists():
                        size_mb = video_path.stat().st_size / 1024 / 1024
                        print(f"  ✓ Downloaded ({size_mb:.1f}MB)")
                        videos.append((match_id, video_path))
                    else:
                        print(f"  ❌ Download failed (file not created)")
                except Exception as e:
                    print(f"  ❌ Download failed: {str(e)[:100]}")
        
        return videos
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("   Make sure Docker containers are running")
        return []


def extract_frames_and_label(videos):
    """Extract frames from videos and label them using current detector."""
    print("\n" + "="*70)
    print("STEP 2: EXTRACTING FRAMES AND AUTO-LABELING WITH CURRENT DETECTOR")
    print("="*70)
    
    if not DETECTOR_PATH.exists():
        print(f"❌ Current detector not found at {DETECTOR_PATH}")
        return 0
    
    print(f"✓ Loading current detector from {DETECTOR_PATH}")
    detector = YOLO(str(DETECTOR_PATH))
    
    frames_output = FRAMES_CACHE / "labeled_frames"
    frames_output.mkdir(exist_ok=True)
    
    images_dir = frames_output / "images"
    labels_dir = frames_output / "labels"
    images_dir.mkdir(exist_ok=True)
    labels_dir.mkdir(exist_ok=True)
    
    total_frames = 0
    
    for match_id, video_path in videos:
        print(f"\n  Match {match_id}: {video_path.name}")
        
        cap = cv2.VideoCapture(str(video_path))
        total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        frame_skip = max(1, total_frames_in_video // FRAMES_PER_VIDEO)
        frame_idx = 0
        extracted = 0
        labeled = 0
        
        print(f"    Total frames: {total_frames_in_video}, FPS: {fps:.1f}")
        print(f"    Extracting every {frame_skip} frames (~{FRAMES_PER_VIDEO} frames)...")
        
        while cap.isOpened() and extracted < FRAMES_PER_VIDEO:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_skip == 0:
                # Save frame
                frame_filename = f"match_{match_id}_frame_{extracted:03d}.jpg"
                frame_path = images_dir / frame_filename
                cv2.imwrite(str(frame_path), frame)
                
                # Detect objects
                results = detector(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
                
                # Save labels in YOLO format
                label_path = labels_dir / frame_filename.replace(".jpg", ".txt")
                
                detections = []
                if results and results[0].boxes:
                    h, w = frame.shape[:2]
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        
                        # Convert to YOLO format (normalized center coordinates)
                        cx = ((x1 + x2) / 2) / w
                        cy = ((y1 + y2) / 2) / h
                        bw = (x2 - x1) / w
                        bh = (y2 - y1) / h
                        
                        # Clamp to [0, 1]
                        cx = max(0, min(1, cx))
                        cy = max(0, min(1, cy))
                        bw = max(0, min(1, bw))
                        bh = max(0, min(1, bh))
                        
                        detections.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                        labeled += 1
                
                with open(label_path, 'w') as f:
                    f.write('\n'.join(detections))
                
                extracted += 1
                total_frames += 1
            
            frame_idx += 1
        
        cap.release()
        print(f"    ✓ Extracted {extracted} frames with {labeled} labeled objects")
    
    print(f"\n✓ Total frames extracted and labeled: {total_frames}")
    print(f"  Images: {images_dir}")
    print(f"  Labels: {labels_dir}")
    
    return total_frames


def combine_datasets():
    """Combine 2026 frames with existing 2024 dataset."""
    print("\n" + "="*70)
    print("STEP 3: COMBINING 2024 + 2026 DATASETS")
    print("="*70)
    
    # Create new dataset directory
    combined_train_img = TRAINING_DIR / "train" / "images"
    combined_train_lbl = TRAINING_DIR / "train" / "labels"
    combined_val_img = TRAINING_DIR / "val" / "images"
    combined_val_lbl = TRAINING_DIR / "val" / "labels"
    
    for d in [combined_train_img, combined_train_lbl, combined_val_img, combined_val_lbl]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Copy existing 2024 training data
    print("  Copying 2024 training data...")
    src_train = FRC_MODEL_DIR / "train"
    for img_file in (src_train / "images").glob("*.jpg"):
        shutil.copy2(img_file, combined_train_img / img_file.name)
    for lbl_file in (src_train / "labels").glob("*.txt"):
        shutil.copy2(lbl_file, combined_train_lbl / lbl_file.name)
    
    count_2024_train = len(list(combined_train_img.glob("*.jpg")))
    print(f"    ✓ Copied {count_2024_train} 2024 training images")
    
    # Copy existing 2024 validation data
    print("  Copying 2024 validation data...")
    src_val = FRC_MODEL_DIR / "val"
    for img_file in (src_val / "images").glob("*.jpg"):
        shutil.copy2(img_file, combined_val_img / img_file.name)
    for lbl_file in (src_val / "labels").glob("*.txt"):
        shutil.copy2(lbl_file, combined_val_lbl / lbl_file.name)
    
    count_2024_val = len(list(combined_val_img.glob("*.jpg")))
    print(f"    ✓ Copied {count_2024_val} 2024 validation images")
    
    # Copy new 2026 frames (use 80% for training, 20% for validation)
    print("  Adding 2026 frames...")
    frames_dir = FRAMES_CACHE / "labeled_frames"
    all_2026_frames = list((frames_dir / "images").glob("*.jpg"))
    
    split_idx = int(len(all_2026_frames) * 0.8)
    train_frames = all_2026_frames[:split_idx]
    val_frames = all_2026_frames[split_idx:]
    
    for img_file in train_frames:
        shutil.copy2(img_file, combined_train_img / img_file.name)
        lbl_file = frames_dir / "labels" / img_file.name.replace(".jpg", ".txt")
        shutil.copy2(lbl_file, combined_train_lbl / lbl_file.name)
    
    for img_file in val_frames:
        shutil.copy2(img_file, combined_val_img / img_file.name)
        lbl_file = frames_dir / "labels" / img_file.name.replace(".jpg", ".txt")
        shutil.copy2(lbl_file, combined_val_lbl / lbl_file.name)
    
    count_2026_train = len(train_frames)
    count_2026_val = len(val_frames)
    print(f"    ✓ Added {count_2026_train} 2026 training images")
    print(f"    ✓ Added {count_2026_val} 2026 validation images")
    
    # Create data.yaml
    data_yaml = {
        "path": str(TRAINING_DIR),
        "train": "train/images",
        "val": "val/images",
        "nc": 2,
        "names": ["note", "robot"]
    }
    
    yaml_path = TRAINING_DIR / "data.yaml"
    import yaml
    with open(yaml_path, 'w') as f:
        yaml.dump(data_yaml, f)
    
    total_train = count_2024_train + count_2026_train
    total_val = count_2024_val + count_2026_val
    
    print(f"\n✓ Combined dataset ready at {TRAINING_DIR}")
    print(f"  Training: {total_train} images ({count_2024_train} 2024 + {count_2026_train} 2026)")
    print(f"  Validation: {total_val} images ({count_2024_val} 2024 + {count_2026_val} 2026)")
    
    return yaml_path


def retrain_model(data_yaml_path):
    """Retrain frc_robot_detector with combined dataset."""
    print("\n" + "="*70)
    print(f"STEP 4: RETRAINING FRC DETECTOR ({TRAINING_EPOCHS} EPOCHS)")
    print("="*70)
    
    print(f"  Loading base model: {DETECTOR_PATH}")
    model = YOLO(str(DETECTOR_PATH))
    
    print(f"  Training configuration:")
    print(f"    Epochs: {TRAINING_EPOCHS}")
    print(f"    Dataset: {data_yaml_path}")
    print(f"    Output: {OUTPUT_MODEL}")
    print(f"    Device: GPU (if available, else CPU)")
    
    results = model.train(
        data=str(data_yaml_path),
        epochs=TRAINING_EPOCHS,
        imgsz=640,
        batch=8,  # Reduced for CPU training
        patience=10,
        device='cpu',  # Use CPU (no GPU available on local machine)
        verbose=True,
        save=True,
        project=str(TRAINING_DIR / "runs"),
        name="train"
    )
    
    # Copy best model to output location
    best_model = TRAINING_DIR / "runs" / "train" / "weights" / "best.pt"
    if best_model.exists():
        shutil.copy2(best_model, OUTPUT_MODEL)
        print(f"\n✓ Best model saved to {OUTPUT_MODEL}")
        print(f"  File size: {OUTPUT_MODEL.stat().st_size / 1024 / 1024:.1f} MB")
        return True
    else:
        print(f"❌ Training failed - best.pt not found")
        return False


def validate_on_test_matches():
    """Test the new model on recent 2026 matches."""
    print("\n" + "="*70)
    print("STEP 5: VALIDATING MODEL ON TEST MATCHES")
    print("="*70)
    
    if not OUTPUT_MODEL.exists():
        print(f"❌ Trained model not found at {OUTPUT_MODEL}")
        return
    
    print(f"✓ Loading trained model from {OUTPUT_MODEL}")
    new_model = YOLO(str(OUTPUT_MODEL))
    old_model = YOLO(str(DETECTOR_PATH))
    
    # Get a few 2026 test matches
    os.chdir(PROJECT_ROOT / "backend")
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))
    
    try:
        from app.db.database import SessionLocal
        from app.models import Match, Event
        
        db = SessionLocal()
        test_matches = db.query(Match).join(Event).filter(
            Event.season_year == 2026,
            Match.video_url.isnot(None)
        ).limit(3).all()
        
        db.close()
        
        if not test_matches:
            print("  No test matches available")
            return
        
        print(f"  Testing on {len(test_matches)} 2026 matches:")
        
        comparison = []
        for match in test_matches:
            # Get a frame from the cached video
            video_path = FRAMES_CACHE / f"match_{match.match_id}.mp4"
            if not video_path.exists():
                continue
            
            cap = cv2.VideoCapture(str(video_path))
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                continue
            
            # Detect with both models
            new_results = new_model(frame, conf=0.3, verbose=False)
            old_results = old_model(frame, conf=0.3, verbose=False)
            
            new_count = len(new_results[0].boxes) if new_results and new_results[0].boxes else 0
            old_count = len(old_results[0].boxes) if old_results and old_results[0].boxes else 0
            
            comparison.append({
                'match_id': match.match_id,
                'old_detections': old_count,
                'new_detections': new_count,
                'improvement': new_count - old_count
            })
            
            print(f"    Match {match.match_id}: {old_count} → {new_count} detections "
                  f"({'+' if new_count > old_count else ''}{new_count - old_count})")
        
        # Summary
        if comparison:
            avg_old = np.mean([c['old_detections'] for c in comparison])
            avg_new = np.mean([c['new_detections'] for c in comparison])
            print(f"\n  Average detections per frame:")
            print(f"    Old model: {avg_old:.1f}")
            print(f"    New model: {avg_new:.1f}")
            print(f"    Improvement: {'+' if avg_new > avg_old else ''}{avg_new - avg_old:.1f} ({((avg_new-avg_old)/avg_old*100) if avg_old > 0 else 0:.0f}%)")
        
    except Exception as e:
        print(f"❌ Validation error: {e}")


def main():
    """Run the complete training pipeline."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*10 + "FRC ROBOT DETECTOR 2026 TRAINING PIPELINE" + " "*17 + "║")
    print("╚" + "="*68 + "╝")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Download videos
        videos = download_match_videos()
        if not videos:
            print("\n⚠️  No videos downloaded. Using cached frames if available.")
        
        # Step 2: Extract and label frames
        if videos or (FRAMES_CACHE / "labeled_frames").exists():
            if videos:
                extracted = extract_frames_and_label(videos)
                if extracted == 0:
                    print("❌ No frames extracted. Exiting.")
                    return
        else:
            print("⚠️  No frames to extract. Skipping to dataset combination.")
        
        # Step 3: Combine datasets
        data_yaml = combine_datasets()
        
        # Step 4: Retrain
        success = retrain_model(data_yaml)
        if not success:
            print("\n❌ Training failed")
            return
        
        # Step 5: Validate
        validate_on_test_matches()
        
        print("\n" + "="*70)
        print("✓ PIPELINE COMPLETE")
        print("="*70)
        print(f"\n  New model: {OUTPUT_MODEL}")
        print(f"  To use it, update docker-compose.yml:")
        print(f"    YOLO_MODEL_PATH: /app/models/frc_robot_detector_v2.pt")
        print(f"\n  Then restart Docker:")
        print(f"    docker-compose restart celery_worker backend")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
