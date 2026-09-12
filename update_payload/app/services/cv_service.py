"""
Computer Vision service.

Keeps the image helpers and the product classifier. The face-recognition
service (Customer Memory) has been removed from the project, along with its
models — so nothing here handles faces any more.
"""

import os

import cv2
import numpy as np
import joblib  # noqa: F401  (kept: other services import joblib through here historically)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
PRODUCT_MODEL_PATH = os.path.join(MODEL_DIR, "product_classifier.h5")


def to_grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def resize_image(img, width=224, height=224):
    return cv2.resize(img, (width, height))


def blur_image(img, k=5):
    return cv2.GaussianBlur(img, (k, k), 0)


def edge_detect(img):
    gray = to_grayscale(img) if img.ndim == 3 else img
    return cv2.Canny(gray, 100, 200)


class ProductClassifierService:
    CLASS_NAMES = ["accessories", "bags", "clothing", "makeup", "shoes"]

    def __init__(self):
        self.model = None
        if os.path.exists(PRODUCT_MODEL_PATH):
            from tensorflow.keras.models import load_model
            self.model = load_model(PRODUCT_MODEL_PATH)

    def predict(self, img):
        if self.model is None:
            return {"status": "not_trained", "message": "Model not found"}
        img_resized = resize_image(img, 224, 224)
        arr = img_resized.astype("float32")
        arr = np.expand_dims(arr, axis=0)
        preds = self.model.predict(arr, verbose=0)[0]
        idx = int(np.argmax(preds))
        return {"category": self.CLASS_NAMES[idx], "confidence": round(float(preds[idx]), 4)}
