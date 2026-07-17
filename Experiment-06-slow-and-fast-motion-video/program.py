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

slow_writer = make_video_writer(OUTPUT_DIR / "slow_motion.mp4", max(fps / 2, 1), (width, height))
fast_writer = make_video_writer(OUTPUT_DIR / "fast_motion.mp4", fps * 2, (width, height))

while True:
    ok, frame = capture.read()
    if not ok:
        break
    slow_writer.write(frame)
    fast_writer.write(frame)

capture.release()
slow_writer.release()
fast_writer.release()
print("Saved slow_motion.mp4 and fast_motion.mp4")
