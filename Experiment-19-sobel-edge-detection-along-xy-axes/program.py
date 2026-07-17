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
sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
magnitude = cv2.magnitude(sobel_x.astype(np.float32), sobel_y.astype(np.float32))
save_image(OUTPUT_DIR / "sobel_xy.png", normalize_to_uint8(magnitude))
print("Saved:", OUTPUT_DIR / "sobel_xy.png")
