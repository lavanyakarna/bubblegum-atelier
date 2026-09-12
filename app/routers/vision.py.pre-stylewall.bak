import io
import csv
import os
from datetime import datetime

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form

from app.services.cv_service import (
    FaceRecognitionService, ProductClassifierService, detect_faces, to_grayscale, resize_image
)

router = APIRouter(tags=["vision"])

_face_service = None
_product_service = None

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
VISITS_LOG = os.path.join(DATA_DIR, "customer_visits.csv")


def get_face_service():
    global _face_service
    if _face_service is None:
        _face_service = FaceRecognitionService()
    return _face_service


def get_product_service():
    global _product_service
    if _product_service is None:
        _product_service = ProductClassifierService()
    return _product_service


def _read_image(upload_bytes: bytes):
    arr = np.frombuffer(upload_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _log_visit(customer: str, status: str):
    os.makedirs(DATA_DIR, exist_ok=True)
    is_new = not os.path.exists(VISITS_LOG)
    with open(VISITS_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "customer", "status"])
        writer.writerow([datetime.utcnow().isoformat(), customer, status])


@router.post("/recognize-face")
async def recognize_face(file: UploadFile = File(...)):
    img = _read_image(await file.read())
    faces = detect_faces(img)
    if len(faces) == 0:
        return {"status": "no_face_detected"}

    x, y, w, h = faces[0]
    face_crop = to_grayscale(img)[y:y + h, x:x + w]
    face_crop = resize_image(face_crop, 200, 200)

    result = get_face_service().recognize(face_crop)
    _log_visit(result.get("customer", "unknown"), result["status"])
    return result


@router.post("/register-face")
async def register_face(name: str = Form(...), files: list[UploadFile] = File(...)):
    """Upload 3-5 photos of one customer's face to register them for recognition."""
    crops = []
    for f in files:
        img = _read_image(await f.read())
        faces = detect_faces(img)
        if len(faces) == 0:
            continue
        x, y, w, h = faces[0]
        crop = to_grayscale(img)[y:y + h, x:x + w]
        crops.append(resize_image(crop, 200, 200))

    if not crops:
        return {"status": "error", "message": "No face detected in any uploaded image."}

    return get_face_service().register_customer(name, crops)


@router.post("/classify-product")
async def classify_product(file: UploadFile = File(...)):
    img = _read_image(await file.read())
    return get_product_service().predict(img)
