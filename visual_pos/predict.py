"""
FulôFiló — Visual POS Inference
=================================
Runs real-time product detection using the trained YOLOv11 model.
Can use webcam, image file, or video file as input.

Run (webcam):
    uv run python visual_pos/predict.py --source 0

Run (image):
    uv run python visual_pos/predict.py --source path/to/image.jpg

Run (video):
    uv run python visual_pos/predict.py --source path/to/video.mp4
"""

import argparse
from pathlib import Path
import sys

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ ultralytics not installed. Run: uv add ultralytics")
    sys.exit(1)

BASE = Path(__file__).resolve().parent
BEST_WEIGHTS = BASE / "runs" / "fulofilo_v1" / "weights" / "best.pt"

def main():
    parser = argparse.ArgumentParser(description="FulôFiló Visual POS — Product Detection")
    parser.add_argument("--source", default="0", help="Input source: 0=webcam, or file path")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold (0.0–1.0)")
    parser.add_argument("--weights", default=str(BEST_WEIGHTS), help="Path to model weights")
    args = parser.parse_args()

    if not Path(args.weights).exists():
        print(f"❌ Model weights not found: {args.weights}")
        print("   Run `uv run python visual_pos/train.py` first.")
        sys.exit(1)

    model = YOLO(args.weights)
    
    # Convert source to int if webcam
    source = int(args.source) if args.source.isdigit() else args.source
    
    print(f"🎥 Starting detection on: {args.source}")
    print(f"   Confidence threshold: {args.conf}")
    print(f"   Press 'q' to quit\n")

    results = model.predict(
        source=source,
        conf=args.conf,
        device="mps",
        show=True,
        stream=True,
        verbose=False,
    )

    for r in results:
        boxes = r.boxes
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                label  = model.names[cls_id]
                print(f"  Detected: {label} ({conf:.0%})")

if __name__ == "__main__":
    main()
