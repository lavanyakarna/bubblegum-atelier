"""
NLP Service
-----------
- Text preprocessing (cleaning)
- Sentiment analysis (TF-IDF + Logistic Regression)

Run this file directly once to train and save the model:
    python -m app.services.nlp_service
It reads data/reviews.csv and writes:
    app/models/sentiment_model.pkl
    app/models/vectorizer.pkl
"""
import os
import re
import string
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "reviews.csv")

STOPWORDS = {
    "the", "a", "an", "is", "it", "and", "to", "of", "in", "this", "that",
    "was", "for", "on", "with", "as", "at", "but", "are", "be", "or", "i",
}


def clean_text(text: str) -> str:
    """Lowercase, strip punctuation/numbers, remove stopwords."""
    text = text.lower()
    text = re.sub(r"[0-9]+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = [w for w in text.split() if w not in STOPWORDS]
    return " ".join(tokens)


def train_sentiment_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    df["clean_review"] = df["review"].apply(clean_text)

    X_train, X_test, y_train, y_test = train_test_split(
        df["clean_review"], df["sentiment"], test_size=0.25, random_state=42, stratify=df["sentiment"]
    )

    vectorizer = TfidfVectorizer(max_features=3000, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train_vec, y_train)

    print(classification_report(y_test, clf.predict(X_test_vec)))

    joblib.dump(clf, os.path.join(MODEL_DIR, "sentiment_model.pkl"))
    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "vectorizer.pkl"))
    print(f"Saved model + vectorizer to {MODEL_DIR}")


class SentimentService:
    def __init__(self):
        self.model = joblib.load(os.path.join(MODEL_DIR, "sentiment_model.pkl"))
        self.vectorizer = joblib.load(os.path.join(MODEL_DIR, "vectorizer.pkl"))

    def predict(self, text: str) -> dict:
        cleaned = clean_text(text)
        vec = self.vectorizer.transform([cleaned])
        pred = self.model.predict(vec)[0]
        proba = self.model.predict_proba(vec)[0]
        confidence = float(max(proba))
        return {"sentiment": pred, "confidence": round(confidence, 4)}


if __name__ == "__main__":
    train_sentiment_model()
