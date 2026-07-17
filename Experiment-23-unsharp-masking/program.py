from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image, ImageFilter

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

source = Image.open(INPUT_DIR / "sample_image.png").convert("RGB")
sharpened = source.filter(ImageFilter.UnsharpMask(radius=3, percent=180, threshold=4))
sharpened.save(OUTPUT_DIR / "unsharp_mask.png")
print("Saved:", OUTPUT_DIR / "unsharp_mask.png")
