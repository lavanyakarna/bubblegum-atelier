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


def test_cart_no_key_rejected():
    r = client.get("/cart")
    assert r.status_code == 401


def test_cart_flow():
    import uuid
    headers = {"X-API-Key": API_KEY, "X-Customer-Id": f"pytest-{uuid.uuid4()}"}

    # add 2 items
    r = client.post("/cart", json={"product_id": "shoe-001", "qty": 2}, headers=headers)
    assert r.status_code == 201
    assert r.json()["item_count"] == 2

    # update quantity to 1 -> server recomputes total
    r = client.patch("/cart/shoe-001", json={"qty": 1}, headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2499.0

    # checkout intent clears the cart
    r = client.post("/checkout-intent", headers=headers)
    assert r.status_code == 201
    assert "order_intent_id" in r.json()

    r = client.get("/cart", headers=headers)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_identity_flow():
    import uuid
    name = f"Test {uuid.uuid4().hex[:6]}"

    # register
    r = client.post("/identity/register", json={"name": name, "secret": "mango", "role": "shopper"}, headers=HEADERS)
    assert r.status_code == 201
    customer_id = r.json()["customer_id"]

    # same name again -> 409 with Gmail-style suggestions
    r = client.post("/identity/register", json={"name": name, "secret": "mango", "role": "shopper"}, headers=HEADERS)
    assert r.status_code == 409
    assert r.json()["suggestions"]

    # wrong secret -> 403
    r = client.post("/identity/login", json={"name": name, "secret": "wrong"}, headers=HEADERS)
    assert r.status_code == 403

    # correct login -> same customer id (data follows the person)
    r = client.post("/identity/login", json={"name": name, "secret": "mango"}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["customer_id"] == customer_id
