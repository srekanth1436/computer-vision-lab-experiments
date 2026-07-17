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
start = (70, 70)
end = (300, 285)

rectangle_image = image.copy()
cv2.rectangle(rectangle_image, start, end, (0, 0, 255), 4)
extracted = image[start[1]:end[1], start[0]:end[0]].copy()

save_image(OUTPUT_DIR / "rectangle.png", rectangle_image)
save_image(OUTPUT_DIR / "extracted_object.png", extracted)
print("Saved rectangle.png and extracted_object.png")
