"""
Vision router — product photo classification.

Note: the face-recognition endpoints (Customer Memory) were removed from this
router along with the face models. What remains is a single, shopper-friendly
capability: tell me what category this garment photo is.
"""

import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile

from app.services.cv_service import ProductClassifierService

router = APIRouter(tags=["vision"])

_product_service = None


def get_product_service():
    global _product_service
    if _product_service is None:
        _product_service = ProductClassifierService()
    return _product_service


def _read_image(upload_bytes: bytes):
    arr = np.frombuffer(upload_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


@router.post("/classify-product")
async def classify_product(file: UploadFile = File(...)):
    img = _read_image(await file.read())
    if img is None:
        return {"status": "error", "message": "Could not read that image."}
    return get_product_service().predict(img)
