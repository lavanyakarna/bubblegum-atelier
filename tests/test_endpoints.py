import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app, API_KEY

client = TestClient(app)
HEADERS = {"X-API-Key": API_KEY}


def test_root():
    r = client.get("/")
    assert r.status_code == 200


def test_no_api_key_rejected():
    r = client.post("/analyze-sentiment", json={"text": "great product"})
    assert r.status_code == 401


def test_sentiment():
    r = client.post("/analyze-sentiment", json={"text": "This is the best purchase ever"}, headers=HEADERS)
    assert r.status_code == 200
    assert "sentiment" in r.json()


def test_chatbot():
    r = client.post("/chatbot", json={"message": "what are your store hours"}, headers=HEADERS)
    assert r.status_code == 200
    assert "reply" in r.json()


def test_dashboard_stats():
    r = client.get("/dashboard/stats", headers=HEADERS)
    assert r.status_code == 200
