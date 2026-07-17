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

gray = read_image(INPUT_DIR / "sample_image.png", cv2.IMREAD_GRAYSCALE)
_, global_threshold = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
adaptive = cv2.adaptiveThreshold(
    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY, 21, 5
)
_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
save_image(OUTPUT_DIR / "global_threshold.png", global_threshold)
save_image(OUTPUT_DIR / "adaptive_threshold.png", adaptive)
save_image(OUTPUT_DIR / "otsu_threshold.png", otsu)
print("Saved global, adaptive, and Otsu threshold results")
