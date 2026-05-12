# Model Training Improvement Plan - Next Steps

## Issues Identified

### 1. **Too Many Robot Detections** ❌
- **Current**: Detecting 10+ objects instead of 6 robots
- **Likely causes**:
  - False positives (game pieces, field elements being detected as robots)
  - Duplicate detections (same robot detected multiple times)
  - Confidence threshold too low
  - Training data includes non-robot objects

### 2. **Wrong Field Geometry** ❌
- **Current**: Showing incorrect field shape/layout
- **Issue**: Perspective transform calibration doesn't match 2026 FIRST game
- **This is separate from model training** - it's a field calibration issue

### 3. **Short Processing Output** ⏱️
- **Current**: 9 seconds of output for 3+ minute match
- **Likely cause**: Frame sampling rate too aggressive or video encoding issue

---

## Next Steps for Better Training (On Other Computer)

### **Phase 1: Data Collection & Validation**

Before training, ensure your dataset is clean:

```bash
# 1. Verify training dataset structure
ls -la frc_model_2026/train/images/ | wc -l  # Should have hundreds of images
ls -la frc_model_2026/train/labels/ | wc -l  # Should match image count

# 2. Check label files are valid YOLO format
# Each label file should contain only lines like:
# <class_id> <x_center> <y_center> <width> <height>
# Where class_id is 0 (note) or 1 (robot) OR only 0 (robot) if single-class

head frc_model_2026/train/labels/sample.txt
```

**Key validation**:
- ✅ Only robots are labeled (no game pieces)
- ✅ Labels are tight bounding boxes around robots
- ✅ All 6 robots visible in most frames (3 red, 3 blue)
- ✅ Bumper colors clearly visible for team identification
- ✅ Diverse angles, lighting, occlusion levels

### **Phase 2: Training Configuration Adjustments**

Modify your training script with these improvements:

```python
# Key parameters to adjust:

TRAINING_EPOCHS = 150  # Increase from 75 to improve convergence
BATCH_SIZE = 32        # Larger batch for better gradient estimates
PATIENCE = 30          # Early stopping patience

# Use larger, more accurate model
MODEL_SIZE = "m"       # "m" instead of "n" (medium vs nano)
                       # Trade-off: slower but more accurate

# Confidence threshold
CONFIDENCE_THRESHOLD = 0.50  # Increase from 0.20 to reduce false positives

# IoU threshold for NMS (reduces duplicate detections)
IOU_THRESHOLD = 0.45        # Can increase to 0.50-0.60
```

**Recommended training script changes**:

```python
from ultralytics import YOLO
import yaml

# Use yolov8m instead of yolov8n
BASE_MODEL = "yolov8m.pt"  # Medium model (more accurate)

model = YOLO(BASE_MODEL)
model.to("cuda")  # or "mps" for Mac

# Enhanced training config
results = model.train(
    data=str(TRAINING_DIR / "data.yaml"),
    epochs=150,           # More epochs
    imgsz=640,
    batch=32,             # Larger batch
    patience=30,          # Early stopping
    device="cuda",
    
    # Augmentation for robustness
    hsv_h=0.015,         # Image HSV-Hue augmentation
    hsv_s=0.7,           # Image HSV-Saturation augmentation  
    hsv_v=0.4,           # Image HSV-Value augmentation
    degrees=10,          # Rotation
    translate=0.1,       # Translation
    scale=0.5,           # Scale
    flipud=0.5,          # Flip upside-down
    fliplr=0.5,          # Flip left-right
    mosaic=1.0,          # Mosaic augmentation
    
    # Optimization
    optimizer="SGD",     # Or "Adam"
    lr0=0.01,           # Learning rate
    lrf=0.01,           # Final learning rate
    momentum=0.937,
    weight_decay=0.0005,
    
    # Validation
    val=True,
    save=True,
    save_period=10,
)

print(f"Best model: {results.save_dir}/weights/best.pt")
```

### **Phase 3: Dataset Improvements**

Before next training, enhance your dataset:

```bash
# 1. Increase training data diversity
   - Add frames from different matches
   - Include various lighting conditions
   - Add partially occluded robots
   - Include extreme angles

# 2. Class distribution check
python3 -c "
import yaml
with open('frc_model_2026/data.yaml') as f:
    config = yaml.safe_load(f)
print(f\"Classes: {config['names']}\")
print(f\"NC: {config['nc']}\")
"

# 3. Verify data.yaml has correct format
cat frc_model_2026/data.yaml
# Should output:
# path: /path/to/frc_model_2026
# train: train/images
# val: val/images
# nc: 1 or 2          # Number of classes (1 for robot only, 2 for note+robot)
# names: ['robot'] or ['note', 'robot']
```

### **Phase 4: Validation & Testing**

After training, validate thoroughly:

```python
# Test on known matches
model = YOLO("path/to/best.pt")

# Should detect EXACTLY 6 robots per frame
results = model.predict(
    source="test_video.mp4",
    conf=0.50,  # Confidence threshold
    iou=0.45,   # NMS IoU threshold
    verbose=True
)

# Check detection count
for result in results:
    num_detections = len(result.boxes)
    print(f"Frame detections: {num_detections}")
    # Should see ~6 per frame
    
    # Check box coordinates
    for box in result.boxes:
        print(f"  {box.cls}: {box.conf:.2f}")
```

---

## Summary of Changes to Make

| Issue | Fix | Implementation |
|-------|-----|-----------------|
| Too many detections | Larger model + higher confidence | Use yolov8m, conf=0.50+ |
| False positives | Better training data | Ensure only robots labeled |
| Duplicate detections | Higher IoU threshold | NMS IoU ≥ 0.50 |
| Poor accuracy | More training | 150+ epochs, augmentation |
| Overfitting risk | Data augmentation | mosaic, flip, rotate, HSV |

---

## Quick Command to Re-train

```bash
# On the other computer:

# 1. Pull latest code
git pull origin train_dev

# 2. Install requirements
pip install -r requirements-training.txt

# 3. Prepare dataset
python3 train_frc_detector_gpu.py  # First run dataset prep

# 4. Run improved training
python3 -c "
from ultralytics import YOLO

model = YOLO('yolov8m.pt')
results = model.train(
    data='frc_model_2026/data.yaml',
    epochs=150,
    batch=32,
    imgsz=640,
    device='cuda',  # or 'mps' for Mac
    patience=30,
    augment=True,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
)
print(f'Best model saved to: {results.save_dir}')
"

# 5. Test model
python3 test_trained_model.py --video path/to/test_match.mp4

# 6. Transfer back
scp path/to/best.pt your-machine:/path/to/backend/models/frc_robot_detector.pt
```

---

## What to Check After Re-training

✅ **Model validation metrics**:
- mAP > 0.80 (mean Average Precision)
- Recall > 0.85 (catches most robots)
- Precision > 0.80 (minimizes false positives)

✅ **Detection consistency**:
- 6 robots per frame (3 red, 3 blue)
- Stable tracking across frames
- High confidence (> 0.60) on valid detections

✅ **No false positives**:
- Game pieces not detected as robots
- Field elements not detected as robots
- Referee/people not detected

---

## Notes on Other Issues

### Field Map Issue
- **Root cause**: `event_camera_calibration` table or perspective transform
- **Fix**: Calibrate camera perspective for 2026 field dimensions
- **Separate from model**: Won't improve by retraining

### Video Length Issue  
- **Likely cause**: Frame sampling or video encoding
- **Check**: Look at `VideoProcessor.process_video()` frame handling
- **Not a model issue**: Model processes correctly, output encoding may be wrong

**Would you like me to also help with:**
1. ✅ Providing field calibration fix?
2. ✅ Investigating the video output length issue?
