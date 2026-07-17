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

image = read_image(INPUT_DIR / "binary_shapes.png")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
cv2.drawContours(result, contours, -1, (0, 0, 255), 3)
for contour in contours:
    if cv2.contourArea(contour) < 100:
        continue
    x, y, width, height = cv2.boundingRect(contour)
    cv2.rectangle(result, (x, y), (x + width, y + height), (0, 255, 0), 2)
save_image(OUTPUT_DIR / "contours.png", result)
print(f"Detected {len(contours)} contours")
