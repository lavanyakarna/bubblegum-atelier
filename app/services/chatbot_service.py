"""
Chatbot Service
---------------
Hybrid approach:
  1. Try exact/substring rule-based match against known patterns (fast, precise).
  2. Fall back to a TF-IDF + LinearSVC intent classifier trained on data/intents.json.

Run this file directly once to train and save the model:
    python -m app.services.chatbot_service
It writes:
    app/models/chatbot_model.pkl   (contains vectorizer + classifier + intents map)
"""
import os
import json
import random
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
MODEL_DIR = os.path.join(BASE_DIR, "models")
INTENTS_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "intents.json")


def load_intents():
    with open(INTENTS_PATH, "r") as f:
        return json.load(f)["intents"]


def train_chatbot_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    intents = load_intents()

    patterns, tags = [], []
    responses_map = {}
    for intent in intents:
        responses_map[intent["tag"]] = intent["responses"]
        for p in intent["patterns"]:
            patterns.append(p.lower())
            tags.append(intent["tag"])

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(patterns)

    clf = LinearSVC()
    clf.fit(X, tags)

    bundle = {
        "vectorizer": vectorizer,
        "classifier": clf,
        "responses": responses_map,
        "raw_patterns": list(zip(patterns, tags)),  # used for rule-based exact match
    }
    joblib.dump(bundle, os.path.join(MODEL_DIR, "chatbot_model.pkl"))
    print(f"Saved chatbot model to {MODEL_DIR}")


class ChatbotService:
    def __init__(self):
        self.bundle = joblib.load(os.path.join(MODEL_DIR, "chatbot_model.pkl"))
        self.vectorizer = self.bundle["vectorizer"]
        self.classifier = self.bundle["classifier"]
        self.responses = self.bundle["responses"]
        self.raw_patterns = self.bundle["raw_patterns"]

    def _rule_based_match(self, message: str):
        message = message.lower().strip()
        for pattern, tag in self.raw_patterns:
            if pattern in message or message in pattern:
                return tag
        return None

    def get_reply(self, message: str) -> dict:
        tag = self._rule_based_match(message)
        method = "rule"
        if tag is None:
            vec = self.vectorizer.transform([message.lower()])
            tag = self.classifier.predict(vec)[0]
            method = "ml"
        reply = random.choice(self.responses.get(tag, ["Sorry, I didn't understand that."]))
        return {"intent": tag, "reply": reply, "method": method}


if __name__ == "__main__":
    train_chatbot_model()
