"""
FulôFiló — Visual POS Training Script
=======================================
Trains a YOLOv11 model to detect FulôFiló products in real-time.
Optimized for Apple Silicon M3/M4 using MPS backend.

Prerequisites:
    uv add ultralytics

Run:
    uv run python visual_pos/train.py

Results will be saved to: visual_pos/runs/train/
"""

from pathlib import Path
import sys

# Check for images before starting
BASE = Path(__file__).resolve().parent
train_images = list((BASE / "images" / "train").glob("*.jpg")) + \
               list((BASE / "images" / "train").glob("*.png"))

if len(train_images) < 10:
    print("⚠️  Not enough training images found.")
    print(f"   Found: {len(train_images)} images in visual_pos/images/train/")
    print("   Minimum recommended: 50 images per class")
    print("\n📸 HOW TO ADD IMAGES:")
    print("   1. Take photos of each product (5-20 photos per product, various angles)")
    print("   2. Place JPG/PNG files in: visual_pos/images/train/")
    print("   3. Label them using Roboflow (https://roboflow.com) — free tier available")
    print("   4. Export labels in YOLO format to: visual_pos/labels/train/")
    print("   5. Re-run this script")
    sys.exit(0)

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ ultralytics not installed. Run: uv add ultralytics")
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────
DATASET_YAML = BASE / "dataset.yaml"
RUNS_DIR     = BASE / "runs"
RUNS_DIR.mkdir(exist_ok=True)

# ── Load Model ────────────────────────────────────────────────────────────────
# Start from YOLOv11 nano (fastest, best for M3 MPS)
# Options: yolo11n.pt (nano), yolo11s.pt (small), yolo11m.pt (medium)
model = YOLO("yolo11n.pt")

# ── Train ─────────────────────────────────────────────────────────────────────
results = model.train(
    data=str(DATASET_YAML),
    epochs=100,
    imgsz=640,
    batch=16,
    device="mps",          # Apple Silicon GPU
    workers=4,
    project=str(RUNS_DIR),
    name="fulofilo_v1",
    patience=20,           # Early stopping
    save=True,
    plots=True,
    verbose=True,
    # Augmentation (helps with limited data)
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=10.0,
    translate=0.1,
    scale=0.5,
    flipud=0.0,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.1,
)

print(f"\n✅ Training complete!")
print(f"   Best model: {RUNS_DIR}/fulofilo_v1/weights/best.pt")
print(f"   Results:    {RUNS_DIR}/fulofilo_v1/results.png")
