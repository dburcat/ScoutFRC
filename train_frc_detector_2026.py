#!/usr/bin/env python3
"""
Collect 2026 FRC match data, extract frames, combine with 2024 dataset, and retrain
- Queries Docker database for 2026 match URLs
- Downloads videos
- Extracts frames and auto-labels with current detector
- Combines with 2024 training data
- Retrains model with 75 epochs
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
import yt_dlp
import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent
FRC_MODEL_2024 = PROJECT_ROOT / "frc_model"
FRAMES_CACHE = PROJECT_ROOT / ".frames_2026_cache"
TRAINING_DIR = PROJECT_ROOT / "frc_model_2026_complete"
DETECTOR_PATH = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector.pt"
OUTPUT_MODEL = PROJECT_ROOT / "backend" / "models" / "frc_robot_detector_v2.pt"

FRAMES_CACHE.mkdir(exist_ok=True)
TRAINING_DIR.mkdir(exist_ok=True)

# Configuration
FRAMES_TO_EXTRACT_PER_VIDEO = 40
CONFIDENCE_THRESHOLD = 0.25
NUM_2026_MATCHES = 5
TRAINING_EPOCHS = 75
BATCH_SIZE = 8


def get_2026_matches_from_docker():
    """Query Docker database for 2026 match URLs."""
    print("\n" + "="*70)
    print("STEP 1: QUERYING 2026 MATCHES FROM DATABASE")
    print("="*70)
    
    query = f"""
    SELECT m.match_id, e.season_year, m.video_url, e.name 
    FROM match m 
    LEFT JOIN event e ON m.event_id = e.event_id 
    WHERE e.season_year = 2026 AND m.video_url IS NOT NULL 
    LIMIT {NUM_2026_MATCHES};
    """
    
    print(f"  Querying database for 2026 matches...")
    
    result = subprocess.run(
        ["docker-compose", "exec", "postgres", "psql", "-U", "postgres", "-d", "scouterfrc", "-c", query],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  ❌ Database query failed: {result.stderr[:200]}")
        return []
    
    lines = result.stdout.strip().split('\n')
    matches = []
    
    for line in lines:
        if 'match_id' in line or '-' in line or line.strip() == '':
            continue
        
        parts = line.split('|')
        if len(parts) >= 4:
            try:
                match_id = int(parts[0].strip())
                url = parts[2].strip()
                event_name = parts[3].strip()
                
                if url and url != 'None':
                    matches.append({
                        'match_id': match_id,
                        'url': url,
                        'event': event_name
                    })
            except:
                pass
    
    if matches:
        print(f"  ✓ Found {len(matches)} 2026 matches with video URLs:")
        for m in matches:
            print(f"    - Match {m['match_id']}: {m['event']}")
    else:
        print(f"  ⚠️  No 2026 matches found. Using sample matches instead...")
        # Fallback to most recent matches
        result = subprocess.run(
            [
                "docker-compose", "exec", "postgres", "psql", "-U", "postgres", "-d", "scouterfrc", 
                "-c", 
                "SELECT m.match_id, e.season_year, m.video_url FROM match m LEFT JOIN event e ON m.event_id = e.event_id WHERE e.season_year IS NOT NULL AND m.video_url IS NOT NULL ORDER BY m.match_id DESC LIMIT 5;"
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'match_id' in line or '-' in line or line.strip() == '':
                continue
            
            parts = line.split('|')
            if len(parts) >= 3:
                try:
                    match_id = int(parts[0].strip())
                    year = int(parts[1].strip()) if parts[1].strip() else 2026
                    url = parts[2].strip()
                    
                    if url and url != 'None':
                        matches.append({
                            'match_id': match_id,
                            'url': url,
                            'event': f"{year} Season"
                        })
                except:
                    pass
    
    return matches[:NUM_2026_MATCHES]


def download_match_videos(matches):
    """Download videos for matched."""
    print("\n" + "="*70)
    print("STEP 2: DOWNLOADING 2026 MATCH VIDEOS")
    print("="*70)
    
    downloaded = []
    
    for match in matches:
        match_id = match['match_id']
        url = match['url']
        video_path = FRAMES_CACHE / f"match_{match_id}.mp4"
        
        if video_path.exists():
            size_mb = video_path.stat().st_size / 1024 / 1024
            print(f"  ⟳ Match {match_id}: Already cached ({size_mb:.1f}MB)")
            downloaded.append((match_id, video_path))
            continue
        
        print(f"  ⏳ Match {match_id}: Downloading from {url[:60]}...")
        
        try:
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'quiet': True,
                'no_warnings': True,
                'outtmpl': str(video_path.with_suffix('')),
                'socket_timeout': 30,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if video_path.exists():
                size_mb = video_path.stat().st_size / 1024 / 1024
                print(f"    ✓ Downloaded ({size_mb:.1f}MB)")
                downloaded.append((match_id, video_path))
            else:
                print(f"    ❌ Download failed (file not created)")
        except Exception as e:
            print(f"    ❌ Download failed: {str(e)[:80]}")
    
    print(f"\n  ✓ Downloaded {len(downloaded)} videos")
    return downloaded


def extract_and_label_frames(videos):
    """Extract frames and auto-label with current detector."""
    print("\n" + "="*70)
    print("STEP 3: EXTRACTING & LABELING FRAMES FROM 2026 VIDEOS")
    print("="*70)
    
    if not DETECTOR_PATH.exists():
        print(f"  ❌ Detector not found: {DETECTOR_PATH}")
        return 0
    
    print(f"  Loading detector: {DETECTOR_PATH.name}")
    detector = YOLO(str(DETECTOR_PATH))
    
    output_dir = FRAMES_CACHE / "labeled_2026"
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    total_frames = 0
    total_detections = 0
    
    for match_id, video_path in videos:
        print(f"\n  Match {match_id}: {video_path.name}")
        
        cap = cv2.VideoCapture(str(video_path))
        total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        frame_skip = max(1, total_frames_in_video // FRAMES_TO_EXTRACT_PER_VIDEO)
        frame_idx = 0
        extracted = 0
        detections = 0
        
        print(f"    Total: {total_frames_in_video} frames @ {fps:.1f} fps")
        print(f"    Extracting every {frame_skip}th frame...")
        
        while cap.isOpened() and extracted < FRAMES_TO_EXTRACT_PER_VIDEO:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_skip == 0:
                # Save frame
                frame_filename = f"2026_match_{match_id}_frame_{extracted:03d}.jpg"
                frame_path = images_dir / frame_filename
                cv2.imwrite(str(frame_path), frame)
                
                # Detect with current model
                results = detector(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
                
                # Save labels in YOLO format
                label_path = labels_dir / frame_filename.replace(".jpg", ".txt")
                label_lines = []
                
                if results and results[0].boxes:
                    h, w = frame.shape[:2]
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cls = int(box.cls[0].cpu().numpy())
                        
                        # Convert to YOLO normalized format
                        cx = ((x1 + x2) / 2) / w
                        cy = ((y1 + y2) / 2) / h
                        bw = (x2 - x1) / w
                        bh = (y2 - y1) / h
                        
                        # Clamp
                        cx = max(0, min(1, cx))
                        cy = max(0, min(1, cy))
                        bw = max(0, min(1, bw))
                        bh = max(0, min(1, bh))
                        
                        label_lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                        detections += 1
                
                with open(label_path, 'w') as f:
                    f.write('\n'.join(label_lines))
                
                extracted += 1
                total_frames += 1
            
            frame_idx += 1
        
        cap.release()
        total_detections += detections
        print(f"    ✓ Extracted {extracted} frames with {detections} robot detections")
    
    print(f"\n  ✓ Total 2026 frames: {total_frames}")
    print(f"  ✓ Total detections: {total_detections}")
    
    return total_frames


def combine_datasets():
    """Combine 2024 data with extracted 2026 data."""
    print("\n" + "="*70)
    print("STEP 4: COMBINING 2024 + 2026 DATASETS")
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
    
    # Add 2026 data (80/20 split)
    print("  Adding 2026 extracted frames...")
    src_2026 = FRAMES_CACHE / "labeled_2026"
    if (src_2026 / "images").exists():
        all_2026 = list((src_2026 / "images").glob("*.jpg"))
        split_idx = int(len(all_2026) * 0.8)
        
        for img in all_2026[:split_idx]:
            shutil.copy2(img, train_img / img.name)
            lbl_src = src_2026 / "labels" / img.name.replace(".jpg", ".txt")
            lbl_dst = train_lbl / img.name.replace(".jpg", ".txt")
            if lbl_src.exists():
                shutil.copy2(lbl_src, lbl_dst)
        
        for img in all_2026[split_idx:]:
            shutil.copy2(img, val_img / img.name)
            lbl_src = src_2026 / "labels" / img.name.replace(".jpg", ".txt")
            lbl_dst = val_lbl / img.name.replace(".jpg", ".txt")
            if lbl_src.exists():
                shutil.copy2(lbl_src, lbl_dst)
        
        count_2026_train = len(all_2026[:split_idx])
        count_2026_val = len(all_2026[split_idx:])
        print(f"    ✓ Added {len(all_2026)} 2026 images ({count_2026_train} train + {count_2026_val} val)")
    else:
        count_2026_train = count_2026_val = 0
        print(f"    ⚠️  No 2026 frames found")
    
    # Create validation split if needed
    total_train = count_2024_train + count_2026_train
    total_val = count_2024_val + count_2026_val
    
    if total_val == 0:
        print("  Creating train/val split...")
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
    print(f"    Train: {total_train} images (2024: {count_2024_train} + 2026: {count_2026_train})")
    print(f"    Val:   {total_val} images (2024: {count_2024_val} + 2026: {count_2026_val})")
    
    return yaml_path


def retrain_model(data_yaml_path):
    """Retrain with combined dataset."""
    print("\n" + "="*70)
    print(f"STEP 5: RETRAINING WITH 75 EPOCHS (2024 + 2026 DATA)")
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
    print("║" + " "*8 + "FRC DETECTOR 2026 COMPLETE TRAINING PIPELINE" + " "*16 + "║")
    print("╚" + "="*68 + "╝")
    print(f"\n  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Get matches from DB
        matches = get_2026_matches_from_docker()
        if not matches:
            print("\n❌ No matches found. Exiting.")
            return False
        
        # Step 2: Download videos
        videos = download_match_videos(matches)
        if not videos:
            print("\n⚠️  No videos downloaded")
            return False
        
        # Step 3: Extract and label frames
        extracted = extract_and_label_frames(videos)
        if extracted == 0:
            print("\n⚠️  No frames extracted")
        
        # Step 4: Combine datasets
        data_yaml = combine_datasets()
        
        # Step 5: Retrain
        success = retrain_model(data_yaml)
        
        if success:
            print("\n" + "="*70)
            print("✓ PIPELINE COMPLETE - 2026 MODEL READY")
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
