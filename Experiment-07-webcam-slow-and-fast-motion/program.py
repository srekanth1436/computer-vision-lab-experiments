from pathlib import Path
import sys
import cv2
import numpy as np
import argparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from cv_utils import (
    ensure_output_dir,
    make_video_writer,
    normalize_to_uint8,
    open_video,
    read_image,
    save_image,
)

INPUT_DIR = HERE / "input"
OUTPUT_DIR = ensure_output_dir(HERE / "output")

parser = argparse.ArgumentParser(description="Webcam slow/fast display")
parser.add_argument("--camera", type=int, default=0, help="Webcam index")
args = parser.parse_args()

capture = cv2.VideoCapture(args.camera)
if not capture.isOpened():
    raise RuntimeError("Could not open webcam. Check camera permission and camera index.")

print("Press Q to close the webcam windows.")
while True:
    ok, frame = capture.read()
    if not ok:
        break
    slow_view = cv2.resize(frame, None, fx=0.5, fy=0.5)
    fast_view = cv2.resize(frame, None, fx=1.5, fy=1.5)
    cv2.imshow("Slow / Smaller View", slow_view)
    cv2.imshow("Fast / Larger View", fast_view)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

capture.release()
cv2.destroyAllWindows()
