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


# --------------------------------------------------------------------------- Style Wall

def _sample_jpg_bytes(color=(120, 180, 240)):
    """A tiny in-memory JPEG so we can exercise the upload path without a fixture file."""
    import cv2
    import numpy as np
    img = np.zeros((240, 240, 3), dtype="uint8")
    img[:, :] = color
    cv2.rectangle(img, (60, 60), (180, 180), (255, 255, 255), -1)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    assert ok
    return buf.tobytes()


def test_stylewall_requires_key():
    r = client.get("/stylewall/posts")
    assert r.status_code == 401


def test_stylewall_rejects_bad_rating():
    r = client.post(
        "/stylewall/posts",
        files={"photo": ("look.jpg", _sample_jpg_bytes(), "image/jpeg")},
        data={"rating": 9, "caption": "too many stars", "customer": "pytest-wall"},
        headers=HEADERS,
    )
    assert r.status_code == 400


def test_stylewall_rejects_non_image():
    r = client.post(
        "/stylewall/posts",
        files={"photo": ("notes.txt", b"this is not a photo", "text/plain")},
        data={"rating": 5, "caption": "oops", "customer": "pytest-wall"},
        headers=HEADERS,
    )
    assert r.status_code == 400


def test_stylewall_post_appears_in_feed():
    r = client.post(
        "/stylewall/posts",
        files={"photo": ("look.jpg", _sample_jpg_bytes(), "image/jpeg")},
        data={"rating": 5, "caption": "Absolutely love this bag, the colour is perfect", "customer": "pytest-wall"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    post = r.json()
    assert post["rating"] == 5
    assert post["photo_url"].startswith("/static/stylewall/")
    assert post["customer"] == "pytest-wall"
    assert post["cheer_count"] == 0
    assert post["comment_count"] == 0
    # sentiment is a bonus - if the model is trained it must come back labelled
    if post["sentiment"] is not None:
        assert post["sentiment"]["sentiment"] in {"positive", "neutral", "negative"}

    feed = client.get("/stylewall/posts?customer=pytest-wall", headers=HEADERS)
    assert feed.status_code == 200
    ids = [p["id"] for p in feed.json()["posts"]]
    assert post["id"] in ids


def test_stylewall_cheer_toggles_and_comments():
    created = client.post(
        "/stylewall/posts",
        files={"photo": ("look.jpg", _sample_jpg_bytes((200, 120, 90)), "image/jpeg")},
        data={"rating": 4, "caption": "Cute shoes, slightly snug", "customer": "pytest-cheerer"},
        headers=HEADERS,
    )
    post_id = created.json()["id"]

    first = client.post(f"/stylewall/posts/{post_id}/cheer", json={"customer": "someone-else"}, headers=HEADERS)
    assert first.status_code == 200
    assert first.json() == {"post_id": post_id, "cheered": True, "cheer_count": 1}

    # same person taps again -> cheer is taken back
    second = client.post(f"/stylewall/posts/{post_id}/cheer", json={"customer": "someone-else"}, headers=HEADERS)
    assert second.json()["cheered"] is False
    assert second.json()["cheer_count"] == 0

    comment = client.post(
        f"/stylewall/posts/{post_id}/comments",
        json={"customer": "another-shopper", "text": "Where did you find this? Looks lovely."},
        headers=HEADERS,
    )
    assert comment.status_code == 201
    assert comment.json()["text"].startswith("Where did you find")

    empty = client.post(f"/stylewall/posts/{post_id}/comments", json={"customer": "x", "text": "   "}, headers=HEADERS)
    assert empty.status_code == 400

    view = client.get("/stylewall/posts?customer=someone-else", headers=HEADERS)
    target = [p for p in view.json()["posts"] if p["id"] == post_id][0]
    assert target["comment_count"] == 1
    assert target["cheered"] is False


def test_stylewall_comment_on_missing_post_is_404():
    r = client.post("/stylewall/posts/does-not-exist/comments", json={"customer": "x", "text": "hi"}, headers=HEADERS)
    assert r.status_code == 404


def test_stylewall_summary():
    r = client.get("/stylewall/summary", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert {"posts", "cheers", "comments", "average_rating", "tagged_categories"} <= set(body.keys())
    assert body["posts"] >= 1


# --------------------------------------------------------------------------- Customer Memory is gone

def test_customer_memory_endpoints_removed():
    for path in ("/recognize-face", "/register-face"):
        r = client.post(path, headers=HEADERS)
        assert r.status_code == 404, f"{path} should no longer exist"


def test_vision_classifier_still_requires_key():
    r = client.post(
        "/classify-product",
        files={"file": ("look.jpg", _sample_jpg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 401
