from fastapi import APIRouter, HTTPException
from app.schemas import SentimentRequest, SentimentResponse
from app.services.nlp_service import SentimentService

router = APIRouter(tags=["nlp"])

_sentiment_service = None


def get_sentiment_service():
    global _sentiment_service
    if _sentiment_service is None:
        try:
            _sentiment_service = SentimentService()
        except FileNotFoundError:
            raise HTTPException(
                status_code=503,
                detail="Sentiment model not trained yet. Run: python -m app.services.nlp_service",
            )
    return _sentiment_service


@router.post("/analyze-sentiment", response_model=SentimentResponse)
def analyze_sentiment(payload: SentimentRequest):
    service = get_sentiment_service()
    result = service.predict(payload.text)
    return result
