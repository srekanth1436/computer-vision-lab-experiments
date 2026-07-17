"""Shared utility functions for the Computer Vision lab experiments."""

from pathlib import Path
import cv2
import numpy as np


def read_image(path: Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    image = cv2.imread(str(path), flags)
    if image is None:
        raise FileNotFoundError(f"Could not read input image: {path}")
    return image


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Could not write output image: {path}")


def normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def open_video(path: Path) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Could not open input video: {path}")
    return capture


def make_video_writer(path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, size)
    if not writer.isOpened():
        raise OSError(f"Could not create output video: {path}")
    return writer
