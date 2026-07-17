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
source = np.float32([[60, 60], [width - 70, 75], [80, height - 70]])
target = np.float32([[30, 100], [width - 90, 35], [125, height - 35]])
matrix = cv2.getAffineTransform(source, target)
result = cv2.warpAffine(image, matrix, (width, height))
save_image(OUTPUT_DIR / "affine_transformed.png", result)
print("Saved:", OUTPUT_DIR / "affine_transformed.png")
