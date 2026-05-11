#!/usr/bin/env python3
"""
Option C: Hybrid 2026 Training Pipeline
- Extract frames from processed matches in database
- Use movement_track bounding boxes as labels
- Combine with 2024 training data
- Retrain with 75 epochs
"""

import subprocess
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import shutil
import cv2
import numpy as np
from ultralytics import YOLO
import yaml
import sqlite3
from io import BytesIO

# Paths
PROJECT_ROOT = Path(__file__).parent
FRC_MODEL_2024 = PROJECT_ROOT / "frc_model"
FRAMES_CACHE = PROJECT_ROOT / ".frames_processed_cache"
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_hybrid"
DETECTOR_PATH = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"

FRAMES_CACHE.mkdir(exist_ok=True)
TRAINING_DIR.mkdir(exist_ok=True)

# Configuration
FRAMES_PER_MATCH = 30
CONFIDENCE_THRESHOLD = 0.25
TRAINING_EPOCHS = 75
BATCH_SIZE = 8


def get_processed_matches_from_db():
    """Query Docker database for matches with movement tracking data."""
    print("\n" + "="*70)
    print("STEP 1: FINDING PROCESSED MATCHES IN DATABASE")
    print("="*70)
    
    # Get matches with movement_track data
    query = """
    SELECT DISTINCT m.match_id, e.season_year, m.video_url, COUNT(mt.track_id) as track_count
    FROM match m
    LEFT JOIN event e ON m.event_id = e.event_id
    LEFT JOIN movement_track mt ON m.match_id = mt.match_id
    WHERE mt.track_id IS NOT NULL
    GROUP BY m.match_id, e.season_year, m.video_url
    ORDER BY m.match_id DESC
    LIMIT 10;
    """
    
    print(f"  Querying for matches with movement_track data...")
    
    result = subprocess.run(
        ["docker-compose", "exec", "postgres", "psql", "-U", "postgres", "-d", "scouterfrc", "-c", query],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  ❌ Query failed: {result.stderr[:200]}")
        return []
    
    lines = result.stdout.strip().split('\n')
    matches = []
    
    for line in lines:
        if 'match_id' in line or '-' in line or line.strip() == '':
            continue
        
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 4:
            try:
                match_id = int(parts[0])
                year = int(parts[1]) if parts[1] else 2026
                url = parts[2] if parts[2] != 'None' else None
                track_count = int(parts[3])
                
                matches.append({
                    'match_id': match_id,
                    'year': year,
                    'url': url,
                    'track_count': track_count
                })
            except:
                pass
    
    if matches:
        print(f"  ✓ Found {len(matches)} matches with tracking data:")
        for m in matches:
            print(f"    - Match {m['match_id']} ({m['year']}): {m['track_count']} tracks")
    else:
        print(f"  ⚠️  No matches with tracking data found")
    
    return matches


def get_movement_data_for_match(match_id):
    """Get all movement_track data for a match."""
    query = f"""
    SELECT track_id, field_x, field_y, timestamp_ms, confidence
    FROM movement_track
    WHERE match_id = {match_id}
    ORDER BY timestamp_ms;
    """
    
    result = subprocess.run(
        ["docker-compose", "exec", "postgres", "psql", "-U", "postgres", "-d", "scouterfrc", "-c", query],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    tracks = {}
    lines = result.stdout.strip().split('\n')
    
    for line in lines:
        if 'track_id' in line or '-' in line or line.strip() == '':
            continue
        
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 5:
            try:
                track_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                ts = int(parts[3])
                conf = float(parts[4])
                
                if track_id not in tracks:
                    tracks[track_id] = []
                tracks[track_id].append({
                    'x': x,
                    'y': y,
                    'timestamp_ms': ts,
                    'confidence': conf
                })
            except:
                pass
    
    return tracks


def download_or_find_video(match_id, video_url):
    """Download video or find it locally."""
    video_path = FRAMES_CACHE / f"match_{match_id}.mp4"
    
    if video_path.exists():
        return video_path
    
    if not video_url:
        return None
    
    print(f"    ⏳ Downloading video... ", end='', flush=True)
    
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'quiet': True,
            'no_warnings': True,
            'outtmpl': str(video_path.with_suffix('')),
            'socket_timeout': 30,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        if video_path.exists():
            print("✓")
            return video_path
    except:
        pass
    
    print("✗ (skipping)")
    return None


def extract_frames_with_labels(matches):
    """Extract frames from processed matches and create labels from movement_track."""
    print("\n" + "="*70)
    print("STEP 2: EXTRACTING FRAMES & CREATING LABELS FROM TRACKING DATA")
    print("="*70)
    
    output_dir = FRAMES_CACHE / "labeled_processed"
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    total_frames = 0
    total_boxes = 0
    
    # FRC field dimensions (in feet)
    FIELD_WIDTH = 54.0  # x-axis
    FIELD_HEIGHT = 27.0  # y-axis
    
    for match_idx, match in enumerate(matches[:5]):  # Limit to 5 matches
        match_id = match['match_id']
        print(f"\n  Match {match_id}:")
        
        # Get tracking data
        tracks = get_movement_data_for_match(match_id)
        if not tracks:
            print(f"    ⚠️  No tracking data")
            continue
        
        # Try to get video
        video_path = download_or_find_video(match_id, match['url'])
        if not video_path:
            print(f"    ⚠️  No video available")
            continue
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"    ❌ Cannot open video")
            continue
        
        total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"    Video: {total_frames_in_video} frames @ {fps:.1f} fps")
        
        # Sample frames evenly
        frame_skip = max(1, total_frames_in_video // FRAMES_PER_MATCH)
        frame_idx = 0
        extracted = 0
        total_boxes_in_match = 0
        
        print(f"    Extracting every {frame_skip}th frame...")
        
        while cap.isOpened() and extracted < FRAMES_PER_MATCH:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_skip == 0:
                # Get timestamp for this frame
                timestamp_ms = int((frame_idx / fps) * 1000)
                
                # Create label for this frame
                label_lines = []
                boxes_in_frame = 0
                
                # For each track, find bounding box at this timestamp
                h_frame, w_frame = frame.shape[:2]
                
                for track_id, points in tracks.items():
                    # Find closest point to this timestamp
                    closest_point = min(points, key=lambda p: abs(p['timestamp_ms'] - timestamp_ms))
                    
                    # Only use if close enough (within 100ms)
                    if abs(closest_point['timestamp_ms'] - timestamp_ms) < 100:
                        x_field = closest_point['x']
                        y_field = closest_point['y']
                        conf = closest_point['confidence']
                        
                        # Convert field coordinates to normalized frame coordinates
                        # Field: 54' wide (x), 27' tall (y)
                        # Assume field fills frame (rough approximation)
                        cx_norm = min(1.0, max(0.0, (x_field / FIELD_WIDTH)))
                        cy_norm = min(1.0, max(0.0, (y_field / FIELD_HEIGHT)))
                        
                        # Robot is roughly 2.5 feet square on field
                        robot_size_feet = 2.5
                        w_norm = (robot_size_feet / FIELD_WIDTH)
                        h_norm = (robot_size_feet / FIELD_HEIGHT)
                        
                        # Class: 1 = robot
                        label_lines.append(f"1 {cx_norm:.6f} {cy_norm:.6f} {w_norm:.6f} {h_norm:.6f}")
                        boxes_in_frame += 1
                
                # Save frame only if it has detections
                if label_lines:
                    frame_filename = f"processed_match_{match_id}_frame_{extracted:03d}.jpg"
                    frame_path = images_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    
                    label_path = labels_dir / frame_filename.replace(".jpg", ".txt")
                    with open(label_path, 'w') as f:
                        f.write('\n'.join(label_lines))
                    
                    extracted += 1
                    total_boxes_in_match += boxes_in_frame
                    total_frames += 1
            
            frame_idx += 1
        
        cap.release()
        print(f"    ✓ Extracted {extracted} frames with {total_boxes_in_match} robot boxes")
        total_boxes += total_boxes_in_match
    
    print(f"\n  ✓ Total processed frames: {total_frames}")
    print(f"  ✓ Total robot boxes: {total_boxes}")
    
    return total_frames


def combine_datasets():
    """Combine 2024 data with extracted processed frames."""
    print("\n" + "="*70)
    print("STEP 3: COMBINING 2024 + PROCESSED 2026 DATASETS")
    print("="*70)
    
    train_img = TRAINING_DIR / "train" / "images"
    train_lbl = TRAINING_DIR / "train" / "labels"
    val_img = TRAINING_DIR / "val" / "images"
    val_lbl = TRAINING_DIR / "val" / "labels"
    
    for d in [train_img, train_lbl, val_img, val_lbl]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Copy 2024 training data
    print("  Copying 2024 training data...")
    src_2024_train = FRC_MODEL_2024 / "train"
    for img in (src_2024_train / "images").glob("*.jpg"):
        shutil.copy2(img, train_img / img.name)
    for lbl in (src_2024_train / "labels").glob("*.txt"):
        shutil.copy2(lbl, train_lbl / lbl.name)
    
    count_2024_train = len(list(train_img.glob("*.jpg")))
    print(f"    ✓ Copied {count_2024_train} 2024 images")
    
    # Copy 2024 validation data
    print("  Copying 2024 validation data...")
    src_2024_val = FRC_MODEL_2024 / "val"
    if (src_2024_val / "images").exists():
        for img in (src_2024_val / "images").glob("*.jpg"):
            shutil.copy2(img, val_img / img.name)
        for lbl in (src_2024_val / "labels").glob("*.txt"):
            shutil.copy2(lbl, val_lbl / lbl.name)
    
    count_2024_val = len(list(val_img.glob("*.jpg")))
    
    # Add processed 2026 data (80/20 split)
    print("  Adding processed 2026 frames...")
    src_processed = FRAMES_CACHE / "labeled_processed"
    if (src_processed / "images").exists():
        all_processed = list((src_processed / "images").glob("*.jpg"))
        split_idx = int(len(all_processed) * 0.8)
        
        for img in all_processed[:split_idx]:
            shutil.copy2(img, train_img / img.name)
            lbl_src = src_processed / "labels" / img.name.replace(".jpg", ".txt")
            lbl_dst = train_lbl / img.name.replace(".jpg", ".txt")
            if lbl_src.exists():
                shutil.copy2(lbl_src, lbl_dst)
        
        for img in all_processed[split_idx:]:
            shutil.copy2(img, val_img / img.name)
            lbl_src = src_processed / "labels" / img.name.replace(".jpg", ".txt")
            lbl_dst = val_lbl / img.name.replace(".jpg", ".txt")
            if lbl_src.exists():
                shutil.copy2(lbl_src, lbl_dst)
        
        count_processed_train = len(all_processed[:split_idx])
        count_processed_val = len(all_processed[split_idx:])
        print(f"    ✓ Added {len(all_processed)} processed frames ({count_processed_train} train + {count_processed_val} val)")
    else:
        count_processed_train = count_processed_val = 0
        print(f"    ⚠️  No processed frames found")
    
    # Verify we have data
    total_train = len(list(train_img.glob("*.jpg")))
    total_val = len(list(val_img.glob("*.jpg")))
    
    if total_val == 0 and total_train > 0:
        print("  Creating train/val split from training data...")
        all_train = list(train_img.glob("*.jpg"))
        split_idx = int(len(all_train) * 0.8)
        
        for img in all_train[split_idx:]:
            shutil.move(str(img), val_img / img.name)
            lbl = train_lbl / img.name.replace(".jpg", ".txt")
            if lbl.exists():
                shutil.move(str(lbl), val_lbl / lbl.name)
        
        total_train = len(list(train_img.glob("*.jpg")))
        total_val = len(list(val_img.glob("*.jpg")))
    
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
    
    print(f"\n  ✓ Combined dataset ready:")
    print(f"    Train: {total_train} images (2024: {count_2024_train} + Processed: {count_processed_train})")
    print(f"    Val:   {total_val} images (2024: {count_2024_val} + Processed: {count_processed_val})")
    
    return yaml_path


def retrain_model(data_yaml_path):
    """Retrain with combined dataset."""
    print("\n" + "="*70)
    print(f"STEP 4: RETRAINING WITH 75 EPOCHS (2024 + PROCESSED 2026)")
    print("="*70)
    
    if not DETECTOR_PATH.exists():
        print(f"  ❌ Detector not found: {DETECTOR_PATH}")
        return False
    
    print(f"  Loading: {DETECTOR_PATH.name}")
    model = YOLO(str(DETECTOR_PATH))
    
    print(f"\n  Configuration:")
    print(f"    Epochs: {TRAINING_EPOCHS} (original: 3)")
    print(f"    Batch: {BATCH_SIZE}")
    print(f"    Device: CPU")
    print(f"    Dataset: {len(list((TRAINING_DIR / 'train' / 'images').glob('*.jpg')))} images")
    
    print(f"\n  ⏳ Training (30-60 minutes on CPU)...")
    print(f"     You can monitor progress with: python3 monitor_training.py")
    
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
        
        best_model = TRAINING_DIR / "runs" / "train" / "weights" / "best.pt"
        if best_model.exists():
            shutil.copy2(best_model, OUTPUT_MODEL)
            print(f"\n  ✓ Training complete!")
            print(f"    Model: {OUTPUT_MODEL.name}")
            print(f"    Size: {OUTPUT_MODEL.stat().st_size / 1024 / 1024:.1f} MB")
            return True
        else:
            print(f"  ❌ Training failed - best.pt not found")
            return False
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Run full pipeline."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*10 + "OPTION C: HYBRID 2026 TRAINING PIPELINE" + " "*20 + "║")
    print("║" + " "*5 + "Extract from DB + Combine with 2024 + Retrain" + " "*15 + "║")
    print("╚" + "="*68 + "╝")
    print(f"\n  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Find processed matches
        matches = get_processed_matches_from_db()
        if not matches:
            print("\n❌ No processed matches found in database")
            return False
        
        # Step 2: Extract frames with labels from tracking data
        extracted = extract_frames_with_labels(matches)
        if extracted == 0:
            print("\n⚠️  No frames extracted from processed matches")
        
        # Step 3: Combine datasets
        data_yaml = combine_datasets()
        
        # Step 4: Retrain
        success = retrain_model(data_yaml)
        
        if success:
            print("\n" + "="*70)
            print("✓ HYBRID PIPELINE COMPLETE - 2026 MODEL READY")
            print("="*70)
            print(f"\n  Next: python3 deploy_model.py")
            print()
            return True
        else:
            print("\n❌ Training failed")
            return False
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted")
        return False
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
