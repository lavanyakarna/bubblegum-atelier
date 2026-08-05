from pydantic import BaseModel
from typing import Optional


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


class Product(BaseModel):
    id: str
    name: str
    category: str
    price: float
    currency: str
    description: str
    sizes: list[str]
    in_stock: bool
    image: str


class ProductListResponse(BaseModel):
    products: list[Product]
    count: int