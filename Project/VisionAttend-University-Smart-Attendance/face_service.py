from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Dict, Iterable

import cv2


BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
TRAINER_DIR = BASE_DIR / "trainer"
MODEL_FILE = TRAINER_DIR / "trainer.yml"

CAPTURE_IMAGE_COUNT = 30
MIN_CAPTURE_IMAGES = 20
RECOGNITION_THRESHOLD = 70
REQUIRED_CONFIRMATIONS = 7

DATASET_PATTERN = re.compile(r"User\.(\d+)\.(\d+)\.jpg$", re.IGNORECASE)


def ensure_face_folders() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    TRAINER_DIR.mkdir(parents=True, exist_ok=True)


def student_face_files(student_id: int) -> list[Path]:
    ensure_face_folders()
    return sorted(DATASET_DIR.glob(f"User.{student_id}.*.jpg"))


def count_student_images(student_id: int) -> int:
    return len(student_face_files(student_id))


def model_exists() -> bool:
    return MODEL_FILE.exists() and MODEL_FILE.stat().st_size > 0


def open_camera():
    """Try common laptop and DroidCam camera numbers."""

    for camera_number in [0, 1, 2, 3]:
        camera = None

        if os.name == "nt":
            camera = cv2.VideoCapture(camera_number, cv2.CAP_DSHOW)

        if camera is None or not camera.isOpened():
            if camera is not None:
                camera.release()
            camera = cv2.VideoCapture(camera_number)

        if camera.isOpened():
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            return camera, camera_number

        camera.release()

    return None, None


def load_face_detector():
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    if detector.empty():
        raise RuntimeError("OpenCV face detector could not be loaded.")

    return detector


def capture_student_faces(
    student_id: int,
    student_name: str,
    register_no: str,
    target_count: int = CAPTURE_IMAGE_COUNT,
) -> dict:
    """Open the local camera and capture cropped grayscale face images."""

    ensure_face_folders()

    for old_file in student_face_files(student_id):
        old_file.unlink(missing_ok=True)

    camera, camera_number = open_camera()

    if camera is None:
        return {
            "success": False,
            "captured": 0,
            "message": "Camera could not be opened. Start DroidCam and try again.",
        }

    detector = load_face_detector()
    captured = 0
    last_saved_at = 0.0
    window_name = "VisionAttend - Register Student Face"

    print("\nFace registration started")
    print("Student:", student_name)
    print("Register Number:", register_no)
    print("Camera Number:", camera_number)
    print("Look straight, then slowly turn left and right.")
    print("Press Q or Esc to cancel.\n")

    try:
        while captured < target_count:
            success, frame = camera.read()

            if not success:
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = detector.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(100, 100),
            )

            selected_face = None
            if len(faces) > 0:
                selected_face = max(faces, key=lambda box: box[2] * box[3])

            if selected_face is not None:
                x, y, width, height = selected_face
                face = gray[y:y + height, x:x + width]
                face = cv2.resize(face, (200, 200))

                now = time.time()
                if now - last_saved_at >= 0.18:
                    captured += 1
                    output_file = DATASET_DIR / f"User.{student_id}.{captured}.jpg"
                    cv2.imwrite(str(output_file), face)
                    last_saved_at = now

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + width, y + height),
                    (0, 220, 0),
                    2,
                )

            cv2.putText(
                frame,
                f"Student: {student_name}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"Register No: {register_no}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"Captured: {captured}/{target_count}",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.72,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                "Look straight and slowly turn left/right",
                (20, 140),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                "Press Q or Esc to cancel",
                (20, 175),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), ord("Q"), 27):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    if captured >= MIN_CAPTURE_IMAGES:
        return {
            "success": True,
            "captured": captured,
            "message": f"Captured {captured} face images successfully.",
        }

    return {
        "success": False,
        "captured": captured,
        "message": (
            f"Only {captured} images were captured. "
            f"At least {MIN_CAPTURE_IMAGES} are required."
        ),
    }


def train_face_model() -> dict:
    """Train one LBPH model using all student face images."""

    ensure_face_folders()

    if not hasattr(cv2, "face"):
        return {
            "success": False,
            "message": (
                "cv2.face is unavailable. Install opencv-contrib-python, "
                "not only opencv-python."
            ),
        }

    faces = []
    student_ids = []
    students_found = set()

    for image_path in sorted(DATASET_DIR.glob("User.*.*.jpg")):
        match = DATASET_PATTERN.match(image_path.name)
        if not match:
            continue

        student_id = int(match.group(1))
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)

        if image is None:
            continue

        image = cv2.resize(image, (200, 200))
        faces.append(image)
        student_ids.append(student_id)
        students_found.add(student_id)

    if not faces:
        return {
            "success": False,
            "message": "No captured face images were found in the dataset folder.",
        }

    import numpy as np

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(student_ids))
    recognizer.write(str(MODEL_FILE))

    return {
        "success": True,
        "image_count": len(faces),
        "student_count": len(students_found),
        "message": (
            f"Model trained using {len(faces)} images from "
            f"{len(students_found)} students."
        ),
    }


def recognize_enrolled_students(
    eligible_students: Dict[int, dict],
    max_seconds: int = 600,
) -> dict:
    """
    Recognize only students enrolled in the selected attendance session.

    Returns the recognized database student IDs. The caller saves them to MySQL.
    """

    ensure_face_folders()

    if not model_exists():
        return {
            "success": False,
            "recognized_ids": [],
            "message": "trainer/trainer.yml was not found. Train the face model first.",
        }

    if not hasattr(cv2, "face"):
        return {
            "success": False,
            "recognized_ids": [],
            "message": "cv2.face is unavailable. Install opencv-contrib-python.",
        }

    if not eligible_students:
        return {
            "success": False,
            "recognized_ids": [],
            "message": "No face-registered students are enrolled in this class.",
        }

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_FILE))
    detector = load_face_detector()

    camera, camera_number = open_camera()
    if camera is None:
        return {
            "success": False,
            "recognized_ids": [],
            "message": "Camera could not be opened. Start DroidCam and try again.",
        }

    recognition_counts: dict[int, int] = {}
    recognized_ids: set[int] = set()
    started_at = time.time()
    window_name = "VisionAttend - Face Verification"

    print("\nFace verification started")
    print("Camera Number:", camera_number)
    print("Only enrolled students can receive attendance.")
    print("Press Q or Esc to close.\n")

    try:
        while time.time() - started_at < max_seconds:
            success, frame = camera.read()

            if not success:
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = detector.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(100, 100),
            )

            for x, y, width, height in faces:
                face = gray[y:y + height, x:x + width]
                face = cv2.resize(face, (200, 200))

                predicted_id, distance = recognizer.predict(face)
                student = eligible_students.get(predicted_id)

                if distance < RECOGNITION_THRESHOLD and student:
                    recognition_counts[predicted_id] = (
                        recognition_counts.get(predicted_id, 0) + 1
                    )

                    if recognition_counts[predicted_id] >= REQUIRED_CONFIRMATIONS:
                        recognized_ids.add(predicted_id)

                    if predicted_id in recognized_ids:
                        status = "PRESENT - SAVED IN DRAFT"
                    else:
                        status = (
                            f"VERIFYING {recognition_counts[predicted_id]}"
                            f"/{REQUIRED_CONFIRMATIONS}"
                        )

                    name_text = student["full_name"]
                    register_text = f"Register No: {student['register_no']}"
                    color = (0, 220, 0)
                elif distance < RECOGNITION_THRESHOLD:
                    name_text = "Recognized but not enrolled"
                    register_text = "No attendance for this class"
                    status = "NOT MARKED"
                    color = (0, 165, 255)
                else:
                    name_text = "Unknown Student"
                    register_text = "Face not registered"
                    status = "NOT MARKED"
                    color = (0, 0, 255)

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + width, y + height),
                    color,
                    2,
                )
                cv2.putText(
                    frame,
                    name_text,
                    (x, max(25, y - 55)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    color,
                    2,
                )
                cv2.putText(
                    frame,
                    register_text,
                    (x, max(50, y - 30)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2,
                )
                cv2.putText(
                    frame,
                    status,
                    (x, max(75, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.52,
                    color,
                    2,
                )

            elapsed = int(time.time() - started_at)
            remaining = max(0, max_seconds - elapsed)
            minutes, seconds = divmod(remaining, 60)

            cv2.putText(
                frame,
                f"Draft Present: {len(recognized_ids)}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"Time Left: {minutes:02d}:{seconds:02d}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                "Press Q or Esc when attendance is finished",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), ord("Q"), 27):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    return {
        "success": True,
        "recognized_ids": sorted(recognized_ids),
        "message": f"Face verification completed. Recognized: {len(recognized_ids)}.",
    }
