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
height, width = image.shape[:2]
translation = np.float32([[1, 0, 80], [0, 1, 55]])
moved = cv2.warpAffine(image, translation, (width, height))
save_image(OUTPUT_DIR / "translated.png", moved)
print("Saved:", OUTPUT_DIR / "translated.png")
