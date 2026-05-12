# Next Steps Summary - CV Model Improvement Plan

## What's Wrong (Current Issues)

1. **Too many robot detections** (~10+ instead of 6)
   - Impact: ❌ Inaccurate field visualization
   - Cause: Model needs retraining with better config
   - Priority: 🔴 **HIGH**

2. **Wrong field map shape** (incorrect 2026 game field)
   - Impact: ⚠️ Visualization geometry is wrong
   - Cause: Camera calibration/perspective transform is misconfigured
   - Priority: 🟡 **MEDIUM**

3. **Video output too short** (9 seconds instead of 3+ minutes)
   - Impact: ⚠️ Visualization output is compressed
   - Cause: Likely frame rate or encoding issue in output writer
   - Priority: 🟢 **LOW** (data in database is correct)

---

## What You Need to Do

### **On the Other Computer** 🖥️

**Step 1: Update code**
```bash
cd /path/to/ScouterFRC
git pull origin train_dev
```

**Step 2: Install dependencies**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-training.txt
```

**Step 3: Run improved training**
```bash
python3 train_frc_detector_improved.py
```

This script will:
- ✅ Verify your training dataset
- ✅ Prepare train/val split
- ✅ Train with **yolov8m** (medium model, not nano)
- ✅ Use **150 epochs** (not 75)
- ✅ Apply enhanced data augmentation
- ✅ Use **confidence threshold 0.50** (not 0.20)
- ✅ Save best model to `backend/models/frc_robot_detector_improved.pt`

**Step 4: Test the new model**
```bash
# If you have a test video
python3 test_trained_model.py --model backend/models/frc_robot_detector_improved.pt --video path/to/match.mp4

# Check: Should detect exactly 6 robots per frame (3 red, 3 blue)
```

**Step 5: Transfer back to main computer**
```bash
# Option A: Direct copy
scp backend/models/frc_robot_detector_improved.pt user@main-computer:/path/to/ScouterFRC/backend/models/

# Option B: Rename and push to git
mv backend/models/frc_robot_detector_improved.pt backend/models/frc_robot_detector.pt
git add backend/models/frc_robot_detector.pt
git commit -m "Improved FRC detector - yolov8m trained on 2026 data"
git push origin train_dev
```

---

### **On Your Main Computer** 💻

**Step 1: Get the new model**
```bash
# If using git
git pull origin train_dev

# Or if using scp, rename it
cd /path/to/ScouterFRC/backend/models
mv frc_robot_detector_improved.pt frc_robot_detector.pt
```

**Step 2: Fix field calibration** (MEDIUM priority)

First, identify the correct field corners from a 2026 match video:

```bash
# Run calibration tool (creates a GUI to click corners)
python3 -c "
import cv2
import numpy as np

video_path = 'path/to/2026_match_video.mp4'
cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()

if ret:
    print(f'Frame size: {frame.shape[1]}x{frame.shape[0]}')
    print('Click the 4 field corners: top-left, top-right, bottom-left, bottom-right')
    
    points = []
    def click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])
            cv2.circle(frame, (x, y), 20, (0, 255, 0), -1)
            cv2.imshow('Click corners', frame)
            print(f'Point {len(points)}: ({x}, {y})')
    
    cv2.imshow('Click corners', frame)
    cv2.setMouseCallback('Click corners', click)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print(f'\nUse these in the database:')
    print(f'{points}')

cap.release()
"

# Then update database with calibration
docker compose exec backend python3 << 'EOF'
from app.models.event_camera_calibration import EventCameraCalibration
from app.database import SessionLocal
from app.models.event import Event
import numpy as np
import cv2

db = SessionLocal()
event = db.query(Event).filter(Event.event_key == '2026arc').first()

if event:
    calib = db.query(EventCameraCalibration).filter_by(event_id=event.event_id).first()
    if not calib:
        calib = EventCameraCalibration(event_id=event.event_id)
        db.add(calib)
    
    # PASTE THE POINTS YOU GOT FROM THE GUI
    video_corners = np.array([
        [100, 100],      # Replace with actual values
        [1920-100, 100],
        [100, 1080-100],
        [1920-100, 1080-100]
    ], dtype=np.float32)
    
    # 2026 field dimensions (27 ft x 54 ft, typical)
    field_corners = np.array([
        [0, 0],
        [27, 0],
        [0, 54],
        [27, 54]
    ], dtype=np.float32)
    
    M = cv2.getPerspectiveTransform(video_corners, field_corners)
    
    calib.calibration_matrix = M.tolist()
    calib.field_width = 27.0
    calib.field_length = 54.0
    db.commit()
    print("✓ Calibration updated")
else:
    print("✗ Event 2026arc not found")

db.close()
EOF
```

**Step 3: Redeploy and test**
```bash
# Stop and restart services
docker compose down
docker compose up -d

# Reprocess a match with the new model
docker compose exec postgres psql -U postgres -d scouterfrc -c "
DELETE FROM movement_track WHERE match_id = 522271;
UPDATE match SET processing_status = 'pending' WHERE match_id = 522271;
"

docker compose exec backend python3 -c "
from app.tasks.auto_video_tasks import process_match_video_from_url
task = process_match_video_from_url.apply_async(kwargs={'match_id': 522271}, queue='video')
print(f'Task queued: {task.id}')
"

# Monitor progress
docker compose logs -f celery-worker

# Once complete, check results
docker compose exec postgres psql -U postgres -d scouterfrc -c "
SELECT COUNT(*) as tracks, COUNT(DISTINCT team_id) as teams 
FROM movement_track WHERE match_id = 522271;
"
```

**Step 4: View improved visualization**
```bash
# Open frontend
# http://localhost:3000/events/Arc/matches/1

# You should now see:
# ✅ Exactly 6 robots (3 red, 3 blue)
# ✅ Correct field shape
# ✅ Higher confidence detections
# ✅ Better team identification
```

---

## Expected Improvements

### Before (Current Model)
- ❌ ~10+ detections per frame
- ❌ Many false positives
- ❌ Low confidence scores
- ❌ Unstable tracking

### After (Improved Model)
- ✅ Exactly 6 robots per frame
- ✅ Minimal false positives
- ✅ High confidence scores (> 0.60)
- ✅ Stable tracking across frames
- ✅ Accurate team identification

---

## Files You Need

✅ **For training on other computer:**
- `train_frc_detector_improved.py` - Enhanced training script
- `requirements-training.txt` - Lightweight dependencies
- Your training dataset (`frc_model/train/` and `frc_model/val/`)

✅ **For reference:**
- `TRAINING_QUICK_START.md` - Step-by-step guide
- `TRAINING_IMPROVEMENT_PLAN.md` - Detailed explanation
- `FIXING_VISUALIZATION_ISSUES.md` - Field calibration guide

---

## Timeline Estimate

| Step | Computer | Time | Notes |
|------|----------|------|-------|
| **Setup** | Other | 5 min | Git pull, venv, pip install |
| **Training** | Other | 30-90 min | Depends on GPU (CUDA/MPS faster) |
| **Testing** | Other | 10 min | Verify 6 robots detected |
| **Transfer** | Other | 2 min | SCP or git push |
| **Deploy** | Main | 5 min | docker compose restart |
| **Calibrate** | Main | 15 min | Click field corners, update DB |
| **Reprocess** | Main | 15-45 min | Process match video |
| **View** | Main | 2 min | Open frontend |
| **TOTAL** | - | **1.5-3 hours** | Most is training time (automatic) |

---

## Success Criteria

Once everything is done, verify:

```bash
# 1. Model accuracy
python3 test_trained_model.py --image test_frames/frame_001.jpg
# Should show: 6 robots, high confidence

# 2. Database detections
docker compose exec postgres psql -U postgres -d scouterfrc -c "
  SELECT team_id, COUNT(*) as count FROM movement_track 
  WHERE match_id = 522271 GROUP BY team_id;
"
# Should show: 6 rows (one per team)

# 3. Frontend visualization
# http://localhost:3000
# Should show: 6 robots on correct field map, movement trajectories
```

---

## Troubleshooting

### Training too slow?
Use `yolov8n` instead of `yolov8m` in the script (faster but less accurate)

### Out of GPU memory?
Reduce BATCH_SIZE from 32 to 16 in the script

### Still too many detections after training?
Increase `CONFIDENCE_THRESHOLD` to 0.60 or 0.70 in the detector

### Field map still wrong?
The calibration needs correct field corner points - make sure to click the actual field corners in the video

---

## Next Action 🎯

**Go to the other computer and run:**
```bash
cd /path/to/ScouterFRC
git pull origin train_dev
python3 train_frc_detector_improved.py
```

Then follow this guide step-by-step!

Questions? Check the detailed guides:
- `TRAINING_QUICK_START.md` - Commands and usage
- `TRAINING_IMPROVEMENT_PLAN.md` - Why each parameter matters
- `FIXING_VISUALIZATION_ISSUES.md` - Field and video fixes
