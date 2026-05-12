# Fixing Field Visualization and Video Output Issues

## Issue 1: Wrong Field Map Shape

### Problem
The field visualization is not the correct shape for the 2026 game.

### Root Cause
The **perspective transform** (camera calibration) is configured for the wrong field dimensions.

### Solution: Fix Field Calibration

**Step 1: Check Current Calibration**
```bash
docker compose exec postgres psql -U postgres -d scouterfrc -c "
SELECT event_id, event_key, calibration_matrix, calibration_points 
FROM event_camera_calibration 
LIMIT 1;
"
```

**Step 2: Update 2026 Field Dimensions**

The 2026 field dimensions need to be set correctly. Edit or create the calibration:

```bash
docker compose exec backend python3 -c "
from app.models.event_camera_calibration import EventCameraCalibration
from app.database import SessionLocal
from app.models.event import Event
import numpy as np

db = SessionLocal()

# Get the 2026 Arc event
event = db.query(Event).filter(Event.event_key == '2026arc').first()
if not event:
    print('Event not found. Available events:')
    events = db.query(Event).all()
    for e in events:
        print(f'  {e.event_key}: {e.event_name}')
    db.close()
    exit(1)

# Get or create calibration
calib = db.query(EventCameraCalibration).filter_by(event_id=event.event_id).first()

if not calib:
    calib = EventCameraCalibration(event_id=event.event_id)
    db.add(calib)

# 2026 Field Dimensions (PLACEHOLDER - verify actual game)
# Typical FRC field: ~27 ft x ~54 ft
FIELD_WIDTH = 27.0   # feet
FIELD_LENGTH = 54.0  # feet

# Video frame size (typical)
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# Define 4 corner points of field in video frame (in pixels)
# These are the approximate corners where the field appears in the video
# Adjust these based on your actual video camera angle
video_corners = np.array([
    [100, 100],        # Top-left
    [VIDEO_WIDTH-100, 100],  # Top-right
    [100, VIDEO_HEIGHT-100], # Bottom-left
    [VIDEO_WIDTH-100, VIDEO_HEIGHT-100]  # Bottom-right
], dtype=np.float32)

# Corresponding field coordinates (in feet)
field_corners = np.array([
    [0, 0],                    # Top-left field corner
    [FIELD_WIDTH, 0],          # Top-right field corner
    [0, FIELD_LENGTH],         # Bottom-left field corner
    [FIELD_WIDTH, FIELD_LENGTH]  # Bottom-right field corner
], dtype=np.float32)

# Calculate perspective transform matrix
import cv2
M = cv2.getPerspectiveTransform(video_corners, field_corners)

calib.calibration_matrix = M.tolist()
calib.field_width = FIELD_WIDTH
calib.field_length = FIELD_LENGTH
calib.calibration_points = {
    'video_corners': video_corners.tolist(),
    'field_corners': field_corners.tolist()
}

db.commit()
print(f'✓ Updated calibration for event {event.event_key}')
print(f'  Field: {FIELD_WIDTH} x {FIELD_LENGTH} ft')
print(f'  Video corners: {video_corners.tolist()}')
db.close()
"
```

**Step 3: Get Correct Calibration Points**

For accurate calibration, you need to identify 4 corner points from an actual match video:

```bash
# Run this to get coordinates from a video frame
python3 -c "
import cv2
import numpy as np

video_path = 'path/to/2026_match_video.mp4'
cap = cv2.VideoCapture(video_path)

# Read first frame
ret, frame = cap.read()
if ret:
    print(f'Frame size: {frame.shape[1]}x{frame.shape[0]}')
    print('Identify the 4 field corners in this frame:')
    
    # Display the frame
    cv2.imshow('Field Corners', frame)
    print('Click 4 points: top-left, top-right, bottom-left, bottom-right')
    print('Press ESC when done')
    
    points = []
    def click_event(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])
            cv2.circle(frame, (x, y), 10, (0, 255, 0), -1)
            cv2.imshow('Field Corners', frame)
            print(f'Point {len(points)}: ({x}, {y})')
    
    cv2.setMouseCallback('Field Corners', click_event)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print(f'\nUse these coordinates:')
    print(f'video_corners = np.array({points})')

cap.release()
"
```

---

## Issue 2: Video Output Length (9 seconds instead of 3+ minutes)

### Problem
The output video from the pipeline is only 9 seconds instead of matching the full match length.

### Root Causes

**Cause 1: Frame Sampling Rate Too High**
- If the video is 150 seconds and output is 9 seconds, it's likely sampling at ~17 FPS instead of downsampling
- Default: 10 FPS downsampling, but encoding might be off

**Cause 2: Video Encoding Issue**
- Frame rate (FPS) might not be set correctly in the output writer

**Cause 3: Early Termination**
- Video processor might be stopping early

### Solution: Fix Video Processor

**Step 1: Check Frame Sampling Rate**
```bash
# In docker-compose.yml or environment, look for:
FRAME_SAMPLE_RATE=10  # Should extract 10 frames per second

# Or in code (backend/app/services/video_processor.py):
DEFAULT_FPS = 10  # Extract at 10 FPS
```

**Step 2: Verify Video Writer Configuration**

Edit [backend/app/services/video_processor.py](backend/app/services/video_processor.py):

```python
# Find the part that creates the video writer output
# It should look like:

import cv2

# Get video properties
cap = cv2.VideoCapture(str(video_path))
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# Create output video writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # or 'H264'
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# KEY: fps should match input FPS, not processing FPS
# If you process at 10 FPS but output at source FPS (30), output is 3x longer
```

**Step 3: Disable Intermediate Output Video (Recommended)**

The intermediate output video isn't necessary - the real data is in the database:

```bash
# In backend/app/services/video_processor.py
# Comment out or remove the video writer section if it's just for visualization

# Instead, the visualization is generated from database on-demand in the frontend
```

### Better Solution: Generate Visualization On-Demand

The frontend should generate the field visualization **from the database** instead of from a saved video file:

```bash
# The frontend already does this!
# When you view a match, it queries movement_track data and draws it

# No need to save intermediate video - the database is the source of truth
```

---

## Complete Fix Checklist

### For Model (Too Many Detections)
- [ ] Use `train_frc_detector_improved.py` script
- [ ] Train with yolov8m (medium model)
- [ ] Run 150 epochs
- [ ] Use BATCH_SIZE=32
- [ ] Increase confidence threshold to 0.50+
- [ ] Increase IOU threshold to 0.50+
- [ ] Verify training data only has robots labeled

### For Field Map (Wrong Shape)
- [ ] Identify 4 field corners in a 2026 match video
- [ ] Update `event_camera_calibration` table with correct calibration matrix
- [ ] Set correct field dimensions for 2026
- [ ] Test with a match visualization

### For Video Output (Too Short)
- [ ] Remove intermediate video output (not needed)
- [ ] Verify frontend queries movement_track correctly
- [ ] Output visualization should be generated on-demand from database
- [ ] Check movement_track has correct number of records

---

## Verify Fixes Are Working

```bash
# 1. Test model detections (6 robots only)
python3 test_trained_model.py --image test_frames/frame_001.jpg

# 2. Check field calibration
docker compose exec postgres psql -U postgres -d scouterfrc -c "
SELECT field_width, field_length FROM event_camera_calibration LIMIT 1;
"

# 3. Check movement data for match
docker compose exec postgres psql -U postgres -d scouterfrc -c "
SELECT COUNT(*) as total_tracks, COUNT(DISTINCT team_id) as teams
FROM movement_track WHERE match_id = 522271;
"

# 4. Run match through pipeline
docker compose exec backend python3 -c "
from app.tasks.auto_video_tasks import process_match_video_from_url
task = process_match_video_from_url.apply_async(kwargs={'match_id': 522271}, queue='video')
print(f'Processing match 522271...')
"

# 5. Check frontend visualization loads correctly
# Open: http://localhost:3000/events/Arc/matches/1
```

---

## Next Steps (Priority Order)

1. **HIGH**: Fix model - use `train_frc_detector_improved.py` on other computer
2. **MEDIUM**: Fix field calibration - update camera perspective for 2026
3. **LOW**: Video output - remove intermediate video, use database as source

---

**Note**: The model improvement is the highest priority since it affects accuracy. The field and video issues are visualization issues that don't affect data quality.
