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
kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
laplacian = cv2.filter2D(image, cv2.CV_32F, kernel)
result = normalize_to_uint8(np.abs(laplacian))
save_image(OUTPUT_DIR / "laplacian_negative.png", result)
print("Saved:", OUTPUT_DIR / "laplacian_negative.png")
