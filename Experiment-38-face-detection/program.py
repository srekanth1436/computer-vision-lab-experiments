from pathlib import Path
import sys
import cv2
import numpy as np
import argparse

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

def detect_faces(frame: np.ndarray) -> tuple[np.ndarray, int]:
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if cascade.empty():
        raise RuntimeError("OpenCV Haar cascade could not be loaded.")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    result = frame.copy()
    for x, y, width, height in faces:
        cv2.rectangle(result, (x, y), (x + width, y + height), (0, 255, 0), 3)
        cv2.putText(result, "FACE", (x, max(25, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 150, 0), 2, cv2.LINE_AA)
    return result, len(faces)


parser = argparse.ArgumentParser()
parser.add_argument("--webcam", action="store_true", help="Use live webcam instead of sample image")
args = parser.parse_args()

if args.webcam:
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        raise RuntimeError("Could not open webcam.")
    print("Press Q to close.")
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        result, _ = detect_faces(frame)
        cv2.imshow("Face Detection", result)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    capture.release()
    cv2.destroyAllWindows()
else:
    image = read_image(INPUT_DIR / "face_sample.jpg")
    result, count = detect_faces(image)
    save_image(OUTPUT_DIR / "face_detection.jpg", result)
    print(f"Detected {count} face(s)")
