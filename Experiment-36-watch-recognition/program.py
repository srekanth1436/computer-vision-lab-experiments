from pathlib import Path
import sys
import cv2
import numpy as np


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

image = read_image(INPUT_DIR / "watch.png")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.medianBlur(gray, 5)
circles = cv2.HoughCircles(
    gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
    param1=100, param2=35, minRadius=80, maxRadius=145
)
result = image.copy()
count = 0
if circles is not None:
    circles = np.round(circles[0]).astype(int)
    for x, y, radius in circles:
        cv2.circle(result, (x, y), radius, (0, 255, 0), 4)
        cv2.circle(result, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(result, "WATCH", (x - 65, y - radius - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 120, 0), 3, cv2.LINE_AA)
        count += 1
save_image(OUTPUT_DIR / "watch_detected.png", result)
print(f"Detected {count} watch face(s)")
