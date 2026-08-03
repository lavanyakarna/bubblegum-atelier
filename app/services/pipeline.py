"""
Unified pipeline: loads all three model services once, so FastAPI doesn't
reload models per-request. Import this in main.py at startup.
"""
from app.services.cv_service import FaceRecognitionService, ProductClassifierService
from app.services.nlp_service import SentimentService
from app.services.chatbot_service import ChatbotService


class Pipeline:
    def __init__(self):
        self.face_service = FaceRecognitionService()
        self.product_service = ProductClassifierService()
        try:
            self.sentiment_service = SentimentService()
        except FileNotFoundError:
            self.sentiment_service = None
        try:
            self.chatbot_service = ChatbotService()
        except FileNotFoundError:
            self.chatbot_service = None
