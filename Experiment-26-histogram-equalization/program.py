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
ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
equalized = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
save_image(OUTPUT_DIR / "histogram_equalized.png", equalized)
print("Saved:", OUTPUT_DIR / "histogram_equalized.png")
