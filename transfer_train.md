I need to train a YOLOv8 computer vision model for FRC (Fire/Rescue) robot detection on this computer, then transfer the trained model back to my main machine.

### Setup Requirements:
- Python 3.8+ with dependencies from a requirements.txt file
- Training script: `train_frc_detector_gpu.py` (or similar)
- Training dataset: FRC dataset with images in `frc_model/train/` and `frc_model/val/` directories with YOLO-formatted labels (.txt files)
- Device: Use CUDA for NVIDIA GPU, or CPU if needed

### The Model:
- Base model: YOLOv8 (from ultralytics library)
- Current model location: `backend/models/frc_robot_detector.pt`
- Model is trained to detect 2 classes: "note" and "robot"
- Currently trained with 75 epochs

### Training Steps:
1. Copy the training script and dataset to this computer
2. Install dependencies (pytorch, ultralytics, opencv-python, etc.)
3. Modify the training script to use the appropriate device (cuda/cpu)
4. Run the training script
5. Generate a new `frc_robot_detector.pt` file

### Model Transfer:
- After training completes, the output model file is self-contained and portable
- Just transfer the generated `.pt` file back to my main machine at `backend/models/frc_robot_detector.pt`
- No special processing needed - the model works on any machine with the dependencies

### What I need from you:
- Help me set up the environment and dependencies
- Help me run the training script
- Confirm the output model file is generated correctly
- Provide the model file for transfer

Can you help me with this training workflow?