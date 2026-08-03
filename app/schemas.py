from pydantic import BaseModel


class SentimentRequest(BaseModel):
    text: str


class SentimentResponse(BaseModel):
    sentiment: str
    confidence: float


class ChatbotRequest(BaseModel):
    message: str


class ChatbotResponse(BaseModel):
    intent: str
    reply: str
    method: str


class DashboardStats(BaseModel):
    total_visits: int
    unique_customers: int
    sentiment_breakdown: dict
