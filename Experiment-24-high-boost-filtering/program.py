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

image = read_image(INPUT_DIR / "sample_image.png").astype(np.float32)
blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=3)
boost_factor = 1.5
high_boost = image + boost_factor * (image - blurred)
result = np.clip(high_boost, 0, 255).astype(np.uint8)
save_image(OUTPUT_DIR / "high_boost.png", result)
print("Saved:", OUTPUT_DIR / "high_boost.png")
