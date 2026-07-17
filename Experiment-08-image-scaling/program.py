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
bigger = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
smaller = cv2.resize(image, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
save_image(OUTPUT_DIR / "bigger.png", bigger)
save_image(OUTPUT_DIR / "smaller.png", smaller)
print("Saved bigger.png and smaller.png")
