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

image = read_image(INPUT_DIR / "sample_image.png")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
gradient = cv2.magnitude(gradient_x, gradient_y)
mask = normalize_to_uint8(gradient)
mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
sharpened = cv2.addWeighted(image, 1.0, mask_bgr, 0.65, 0)
save_image(OUTPUT_DIR / "gradient_mask.png", sharpened)
print("Saved:", OUTPUT_DIR / "gradient_mask.png")
