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
edges = cv2.Canny(gray, 100, 200)
save_image(OUTPUT_DIR / "canny_edges.png", edges)
print("Saved:", OUTPUT_DIR / "canny_edges.png")
