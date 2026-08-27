import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.routers.nlp import get_sentiment_service

router = APIRouter(tags=["reviews"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
REVIEWS_PATH = os.path.join(DATA_DIR, "reviews.json")


class ReviewRequest(BaseModel):
    text: str
    product_id: Optional[str] = None
    customer: Optional[str] = None


def _load_reviews():
    if not os.path.exists(REVIEWS_PATH):
        return []
    with open(REVIEWS_PATH) as f:
        return json.load(f)


def _save_reviews(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REVIEWS_PATH, "w") as f:
        json.dump(data, f, indent=2)


@router.post("/reviews")
def create_review(payload: ReviewRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Review text cannot be empty")

    service = get_sentiment_service()
    prediction = service.predict(payload.text)

    review = {
        "id": str(uuid.uuid4())[:8],
        "text": payload.text,
        "product_id": payload.product_id,
        "customer": payload.customer,
        "sentiment": prediction["sentiment"],
        "confidence": prediction.get("confidence"),
        "timestamp": datetime.utcnow().isoformat(),
    }

    reviews = _load_reviews()
    reviews.append(review)
    _save_reviews(reviews)
    return review


@router.get("/reviews")
def list_reviews(product_id: Optional[str] = Query(None), sentiment: Optional[str] = Query(None)):
    reviews = _load_reviews()
    if product_id:
        reviews = [r for r in reviews if r.get("product_id") == product_id]
    if sentiment:
        reviews = [r for r in reviews if r.get("sentiment") == sentiment]
    reviews = sorted(reviews, key=lambda r: r["timestamp"], reverse=True)
    return {"reviews": reviews, "count": len(reviews)}