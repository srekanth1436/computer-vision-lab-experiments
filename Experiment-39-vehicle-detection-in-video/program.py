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
writer = make_video_writer(OUTPUT_DIR / "vehicle_detection.mp4", fps, (width, height))

background_subtractor = cv2.createBackgroundSubtractorMOG2(
    history=80, varThreshold=35, detectShadows=True
)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

while True:
    ok, frame = capture.read()
    if not ok:
        break

    mask = background_subtractor.apply(frame)
    _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = frame.copy()
    for contour in contours:
        if cv2.contourArea(contour) < 900:
            continue
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if y < 120:
            continue
        cv2.rectangle(result, (x, y), (x + box_width, y + box_height), (0, 255, 0), 2)
        cv2.putText(result, "MOVING VEHICLE", (x, max(25, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 120, 0), 2, cv2.LINE_AA)
    writer.write(result)

capture.release()
writer.release()
print("Saved:", OUTPUT_DIR / "vehicle_detection.mp4")
