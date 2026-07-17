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

capture = open_video(INPUT_DIR / "sample_video.mp4")
fps = capture.get(cv2.CAP_PROP_FPS) or 20.0
width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
writer = make_video_writer(OUTPUT_DIR / "perspective_video.mp4", fps, (width, height))

source = np.float32([[0, 0], [width - 1, 0], [0, height - 1], [width - 1, height - 1]])
target = np.float32([[35, 10], [width - 45, 20], [95, height - 1], [width - 95, height - 1]])
matrix = cv2.getPerspectiveTransform(source, target)

while True:
    ok, frame = capture.read()
    if not ok:
        break
    transformed = cv2.warpPerspective(frame, matrix, (width, height))
    writer.write(transformed)

capture.release()
writer.release()
print("Saved:", OUTPUT_DIR / "perspective_video.mp4")
