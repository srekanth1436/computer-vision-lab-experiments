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
target = np.float32([[45, 25], [width - 55, 5], [105, height - 25], [width - 95, height - 5]])
matrix = cv2.getPerspectiveTransform(source, target)
result = cv2.warpPerspective(image, matrix, (width, height))
save_image(OUTPUT_DIR / "perspective_transformed.png", result)
print("Saved:", OUTPUT_DIR / "perspective_transformed.png")
