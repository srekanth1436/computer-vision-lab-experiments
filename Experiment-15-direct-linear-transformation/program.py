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

def compute_homography_dlt(source_points: np.ndarray, target_points: np.ndarray) -> np.ndarray:
    if source_points.shape != (4, 2) or target_points.shape != (4, 2):
        raise ValueError("DLT example expects four 2D source and target points.")

    rows = []
    for (x, y), (u, v) in zip(source_points, target_points):
        rows.append([-x, -y, -1, 0, 0, 0, u*x, u*y, u])
        rows.append([0, 0, 0, -x, -y, -1, v*x, v*y, v])

    matrix = np.asarray(rows, dtype=np.float64)
    _, _, vt = np.linalg.svd(matrix)
    homography = vt[-1].reshape(3, 3)
    return homography / homography[2, 2]


image = read_image(INPUT_DIR / "sample_image.png")
height, width = image.shape[:2]
source = np.float64([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
target = np.float64([[55, 20], [width - 40, 55], [width - 95, height - 35], [75, height - 5]])
homography = compute_homography_dlt(source, target)
result = cv2.warpPerspective(image, homography, (width, height))
save_image(OUTPUT_DIR / "dlt_transformed.png", result)
print("Saved:", OUTPUT_DIR / "dlt_transformed.png")
