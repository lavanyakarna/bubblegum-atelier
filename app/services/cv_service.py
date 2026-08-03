import os
import cv2
import numpy as np
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
FACE_DB_PATH = os.path.join(MODEL_DIR, "face_db.pkl")
FACE_MODEL_PATH = os.path.join(MODEL_DIR, "face_lbph.yml")
PRODUCT_MODEL_PATH = os.path.join(MODEL_DIR, "product_classifier.h5")

HAAR_PATH = os.path.join(MODEL_DIR, "haarcascade_frontalface_default.xml")


def to_grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def resize_image(img, width=224, height=224):
    return cv2.resize(img, (width, height))


def blur_image(img, k=5):
    return cv2.GaussianBlur(img, (k, k), 0)


def edge_detect(img):
    gray = to_grayscale(img) if img.ndim == 3 else img
    return cv2.Canny(gray, 100, 200)


def detect_faces(img):
    gray = to_grayscale(img) if img.ndim == 3 else img
    cascade = cv2.CascadeClassifier(HAAR_PATH)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return faces


class FaceRecognitionService:
    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.label_map = {}
        if os.path.exists(FACE_MODEL_PATH) and os.path.exists(FACE_DB_PATH):
            self.recognizer.read(FACE_MODEL_PATH)
            self.label_map = joblib.load(FACE_DB_PATH)

    def register_customer(self, name: str, face_images: list):
        label = len(self.label_map)
        self.label_map[label] = name
        labels = [label] * len(face_images)
        if os.path.exists(FACE_MODEL_PATH):
            self.recognizer.read(FACE_MODEL_PATH)
            self.recognizer.update(face_images, np.array(labels))
        else:
            self.recognizer.train(face_images, np.array(labels))
        self.recognizer.save(FACE_MODEL_PATH)
        joblib.dump(self.label_map, FACE_DB_PATH)
        return {"status": "registered", "customer": name, "label": label}

    def recognize(self, face_image, threshold=80.0):
        if not self.label_map:
            return {"status": "unknown", "reason": "no customers registered yet"}
        label, distance = self.recognizer.predict(face_image)
        if distance <= threshold:
            return {"status": "recognized", "customer": self.label_map.get(label, "unknown"),
                    "confidence": round(100 - distance, 2)}
        return {"status": "unknown", "distance": round(distance, 2)}


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