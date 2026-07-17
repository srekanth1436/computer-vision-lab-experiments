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

image = read_image(INPUT_DIR / "sample_image.png", cv2.IMREAD_GRAYSCALE)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
eroded = cv2.erode(image, kernel, iterations=1)
save_image(OUTPUT_DIR / "eroded.png", eroded)
print("Saved:", OUTPUT_DIR / "eroded.png")
