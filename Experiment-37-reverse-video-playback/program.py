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

frames = []
while True:
    ok, frame = capture.read()
    if not ok:
        break
    frames.append(frame)
capture.release()

writer = make_video_writer(OUTPUT_DIR / "reverse_video.mp4", fps, (width, height))
for frame in reversed(frames):
    writer.write(frame)
writer.release()
print(f"Saved reverse video with {len(frames)} frames")
