# Training on Other Computer - Quick Start

## Pre-Training Checklist

Before you start training on the other computer, verify:

- [ ] Git repository cloned and up-to-date
- [ ] Training dataset exists: `frc_model/train/` and `frc_model/val/`
- [ ] Labels are valid YOLO format (1 class = robot only, 2 classes = note + robot)
- [ ] Python 3.8+ installed
- [ ] GPU drivers installed (CUDA for NVIDIA, or system GPU for Mac)

---

## Step 1: Setup Environment

```bash
# Clone or update repository
cd /path/to/ScouterFRC
git pull origin train_dev

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install training dependencies
pip install -r requirements-training.txt

# Verify GPU
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU only\"}')"
```

---

## Step 2: Prepare Dataset (Optional - Script Does This)

```bash
# Verify your training data
ls -la frc_model/train/images/ | wc -l
ls -la frc_model/train/labels/ | wc -l

# Should have matching counts (or close with validation set)
# Recommend 300+ images minimum
```

---

## Step 3: Run Improved Training

```bash
# Make script executable
chmod +x train_frc_detector_improved.py

# Run training
python3 train_frc_detector_improved.py

# This will:
# 1. Verify dataset ✓
# 2. Prepare train/val split ✓
# 3. Train with yolov8m (medium model) ✓
# 4. Run validation ✓
# 5. Save best model ✓
```

**Expected output:**
```
═══════════════════════════════════════════════════════════════════════════
FRC ROBOT DETECTOR - IMPROVED TRAINING
Version: yolov8m with Enhanced Config
═══════════════════════════════════════════════════════════════════════════
Project root: /path/to/ScouterFRC
Training dir: /path/to/ScouterFRC/frc_model_2026_gpu_improved
Device: cuda (or mps, or cpu)

STEP 1: VERIFYING DATASET
  ✓ Training images: 320
  ✓ Training labels: 320
  ✓ Validation images: 80
  ✓ Detected 1 class(es): ['robot']

STEP 2: PREPARING DATASET FOR TRAINING
  Collecting all training images...
  Found 400 total images
  ✓ Dataset prepared:
    Train: 320 images
    Val:   80 images

STEP 3: IMPROVED TRAINING
  Model: yolov8m
  Epochs: 150
  Batch: 32
  Device: cuda
  Confidence: 0.5
  
  Training progress: [============================] 150/150 epochs...
  
STEP 4: MODEL EVALUATION
  ✓ Validation Metrics:
    mAP50: 0.95
    mAP50-95: 0.87

STEP 5: SAVING MODEL
  ✓ Model saved at: backend/models/frc_robot_detector_improved.pt

═══════════════════════════════════════════════════════════════════════════
✓ TRAINING COMPLETE
═══════════════════════════════════════════════════════════════════════════
```

**Training time estimate:**
- **GPU (CUDA)**: 30-60 minutes for 150 epochs
- **GPU (Mac M1/M2)**: 45-90 minutes for 150 epochs
- **CPU**: 2-4 hours for 150 epochs

---

## Step 4: Monitor Training (Optional)

In another terminal, watch training progress:

```bash
# On Mac/Linux
tail -f frc_model_2026_gpu_improved/runs/train_improved/results.csv

# Or check intermediate results
ls -lh frc_model_2026_gpu_improved/runs/train_improved/weights/
```

---

## Step 5: Test the Newly Trained Model

```bash
# Copy the test script if you don't have it
# You can test with any video or image

python3 test_trained_model.py --model backend/models/frc_robot_detector_improved.pt --video path/to/test_match.mp4

# Output will be saved to: test_output/model_test_*.mp4
```

**Verify model quality:**
- [ ] Exactly 6 robots detected per frame (3 red, 3 blue)
- [ ] No false positives on game pieces
- [ ] High confidence scores (> 0.60)
- [ ] Consistent tracking across frames
- [ ] No detection flickering

---

## Step 6: Transfer Model Back

Once satisfied with the model:

```bash
# Option A: Direct file transfer
scp backend/models/frc_robot_detector_improved.pt user@your-main-computer:/path/to/ScouterFRC/backend/models/

# Option B: Git push (if model file is tracked)
git add backend/models/frc_robot_detector_improved.pt
git commit -m "New improved FRC detector model - yolov8m trained"
git push origin train_dev

# Then on main computer: git pull origin train_dev
```

---

## Step 7: Deploy on Main Computer

```bash
# Pull changes if using Git
git pull origin train_dev

# If transferred via scp, rename the model
cd /path/to/ScouterFRC/backend/models
mv frc_robot_detector_improved.pt frc_robot_detector.pt

# Restart services
docker compose down
docker compose up -d

# Test with a match
docker compose exec backend python3 -c "
from app.tasks.auto_video_tasks import process_match_video_from_url
task = process_match_video_from_url.apply_async(kwargs={'match_id': 522271}, queue='video')
print(f'Task ID: {task.id}')
"
```

---

## Troubleshooting

### Training too slow
- **Solution**: Use `yolov8n` (nano) instead of `yolov8m` in the script
- **Trade-off**: Faster training, but less accurate

### Out of memory (CUDA)
- **Solution**: Reduce `BATCH_SIZE` from 32 to 16 or 8
- **Edit**: Line ~60 in `train_frc_detector_improved.py`

### Training not converging
- **Solution**: Increase `PATIENCE` from 30 to 50
- **Or**: Use `TRAINING_EPOCHS = 200` instead of 150

### GPU not detected
```bash
python3 -c "import torch; print(torch.cuda.is_available())"

# If False:
# - NVIDIA: Install CUDA toolkit and cuDNN
# - Mac: Update to macOS 12.3+
# - Fallback: Training will use CPU (slower)
```

### Model still has too many detections
- **Increase confidence threshold**: `CONFIDENCE_THRESHOLD = 0.60` or higher
- **Increase IOU threshold**: `IOU_THRESHOLD = 0.60` for NMS
- **Check training data**: Ensure only robots are labeled, not game pieces

---

## Key Improvements in This Training

| Change | Reason | Impact |
|--------|--------|--------|
| **yolov8m** → medium | Larger model = better accuracy | +5-10% mAP improvement |
| **75 → 150 epochs** | More training = better convergence | Better recall |
| **0.20 → 0.50 confidence** | Filter false positives | Fewer false detections |
| **0.45 → 0.50 IOU** | Stricter NMS | Fewer duplicate detections |
| **32 batch size** | Stable gradients | Better generalization |
| **Data augmentation** | More robustness | Better in various conditions |

---

## Success Criteria

After training, your model should achieve:

✅ **mAP > 0.80** (validation metric)  
✅ **Recall > 0.85** (catches most robots)  
✅ **Precision > 0.80** (minimizes false positives)  
✅ **6 robots per frame** (3 red, 3 blue)  
✅ **< 100ms per frame** (inference speed)  

If these aren't met, you may need to:
1. Collect more diverse training data
2. Fix label quality (ensure only robots are labeled)
3. Run training again with more epochs

---

## Next Steps After Training

1. ✅ Test on test video (`test_trained_model.py`)
2. ✅ Transfer model to main computer
3. ✅ Run through full pipeline with match video
4. ✅ Check field visualization shows 6 robots (3 red, 3 blue)
5. ✅ Verify team numbers are correctly identified
6. ⚠️ If still too many detections, increase confidence threshold further
7. ⚠️ If field map is wrong, that's a separate calibration issue (not model)

---

**Questions?** Check `TRAINING_IMPROVEMENT_PLAN.md` for detailed explanation of each parameter.
