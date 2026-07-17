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
source = np.float32([[0, 0], [width - 1, 0], [0, height - 1], [width - 1, height - 1]])
target = np.float32([[40, 40], [width - 80, 15], [20, int(height * 0.72)], [width - 20, int(height * 0.82)]])
homography, status = cv2.findHomography(source, target)
if homography is None:
    raise RuntimeError("Homography could not be estimated.")
result = cv2.warpPerspective(image, homography, (width, height))
save_image(OUTPUT_DIR / "homography.png", result)
print("Saved:", OUTPUT_DIR / "homography.png")
