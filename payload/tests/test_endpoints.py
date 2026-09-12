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


# --------------------------------------------------------------------------- Insights (owner dashboard)
# Every number here must come from real recorded data, never sample text.

def _seed_events():
    """A few guaranteed-real events so the insights have something to read."""
    for _ in range(3):
        client.post("/events", json={"type": "view", "product_id": "shoe-001",
                                     "meta": {"context": "pytest"}},
                    headers={**HEADERS, "X-Customer-Id": "pytest-insights"})
    client.post("/events", json={"type": "cart_add", "product_id": "shoe-001", "meta": {"qty": 1}},
                headers={**HEADERS, "X-Customer-Id": "pytest-insights"})


def test_insights_require_key():
    for path in ("/insights", "/insights/visits", "/insights/customers", "/insights/chats", "/insights/tagged"):
        assert client.get(path).status_code == 401, path


def test_insights_cards_are_real():
    _seed_events()
    r = client.get("/insights", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["insights"], "expected at least one insight card"
    assert body["events_considered"] >= 4
    totals = body["totals"]
    assert totals["visits"] >= 3
    assert totals["customers"] >= 1
    for card in body["insights"]:
        assert card["title"] and card["text"]
        # no leftovers from the old sample text
        assert "recognized at the door" not in card["text"].lower()


def test_insights_visits_detail():
    _seed_events()
    r = client.get("/insights/visits", headers=HEADERS)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 3
    assert len(d["days"]) == 7
    assert d["top_products"], "expected most-viewed products"
    top = d["top_products"][0]
    assert top["views"] >= 1
    assert top["name"], "top product should carry its catalogue name"
    assert d["top_categories"]


def test_insights_customers_detail():
    _seed_events()
    r = client.get("/insights/customers", headers=HEADERS)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all("label" in c for c in d["customers"])
    # guest ids are masked - never the raw id
    assert all(not c["label"].startswith("guest-") for c in d["customers"])


def test_chatbot_records_the_conversation():
    before = client.get("/insights/chats", headers=HEADERS).json()["total"]
    r = client.post("/chatbot", json={"message": "what are your store hours"},
                    headers={**HEADERS, "X-Customer-Id": "pytest-chatter"})
    assert r.status_code == 200

    after = client.get("/insights/chats", headers=HEADERS).json()
    assert after["total"] == before + 1
    assert after["recent"][0]["message"] == "what are your store hours"
    assert after["recent"][0]["reply"]


def test_tagged_endpoint_shape():
    r = client.get("/insights/tagged", headers=HEADERS)
    assert r.status_code == 200
    d = r.json()
    assert {"total", "by_category", "recent"} <= set(d.keys())


def test_stylewall_upload_feeds_the_tagged_counter(monkeypatch):
    """A wall upload runs the vision model - that should show up as a real tag count."""
    import app.routers.stylewall as sw
    monkeypatch.setattr(sw, "_read_category", lambda img: {"category": "bags", "confidence": 0.91})

    before = client.get("/insights/tagged", headers=HEADERS).json()["total"]

    r = client.post(
        "/stylewall/posts",
        files={"photo": ("look.jpg", _sample_jpg_bytes((90, 140, 200)), "image/jpeg")},
        data={"rating": 5, "caption": "my new bag", "customer": "pytest-tagger"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["cv_tag"]["category"] == "bags"

    after = client.get("/insights/tagged", headers=HEADERS).json()
    assert after["total"] == before + 1
    assert after["recent"][0]["category"] == "bags"
    assert after["recent"][0]["source"] == "style_wall"


# --------------------------------------------------------------------------- Lookbook likes

def test_lookbook_likes_require_key():
    assert client.get("/lookbook/likes").status_code == 401


def test_lookbook_like_toggles():
    import uuid
    look = "look-2"
    # fresh names every run, so the test never depends on a previous run's leftovers
    me = f"pytest-fan-{uuid.uuid4().hex[:6]}"
    other = f"pytest-other-{uuid.uuid4().hex[:6]}"

    def like_count(who):
        data = client.get(f"/lookbook/likes?customer={who}", headers=HEADERS).json()
        return data["looks"].get(look, {}).get("count", 0)

    start_count = like_count(me)

    first = client.post(f"/lookbook/{look}/like", json={"customer": me}, headers=HEADERS)
    assert first.status_code == 200
    assert first.json() == {"look_id": look, "liked": True, "like_count": start_count + 1}

    # the same shopper tapping again takes the like back
    second = client.post(f"/lookbook/{look}/like", json={"customer": me}, headers=HEADERS)
    assert second.json()["liked"] is False
    assert second.json()["like_count"] == start_count

    # a different shopper can like the same look
    third = client.post(f"/lookbook/{look}/like", json={"customer": other}, headers=HEADERS)
    assert third.json()["like_count"] == start_count + 1

    listing = client.get(f"/lookbook/likes?customer={other}", headers=HEADERS).json()
    assert listing["looks"][look]["liked"] is True
    assert listing["total_likes"] >= 1


def test_lookbook_like_validation():
    assert client.post("/lookbook/look-1/like", json={"customer": "  "}, headers=HEADERS).status_code == 400


# --------------------------------------------------------------------------- Concierge (chatbot) quality

def _ask(question):
    r = client.post("/chatbot", json={"message": question}, headers=HEADERS)
    assert r.status_code == 200
    return r.json()


def test_concierge_greets_a_greeting():
    assert _ask("hi")["intent"] == "greeting"


def test_concierge_is_not_fooled_by_substrings():
    """The old matcher saw the greeting 'hi' inside 'shipping' and 'which'."""
    assert _ask("how much is shipping")["intent"] != "greeting"
    assert _ask("which items are new")["intent"] != "greeting"


def test_concierge_lists_real_products_with_prices():
    reply = _ask("show me bags")
    assert reply["intent"] == "category_lookup"
    assert reply["method"] == "catalogue"
    assert "INR" in reply["reply"]


def test_concierge_quotes_the_real_price_of_a_named_piece():
    products = client.get("/products", headers=HEADERS).json()["products"]
    target = next(p for p in products if p["id"] == "shoe-001")
    reply = _ask(f"how much are the {target['name'].lower()}")
    assert reply["intent"] == "product_lookup"
    assert str(int(float(target["price"]))) in reply["reply"]   # 2499, not 2499.0
    assert target["name"] in reply["reply"]


def test_concierge_prefers_policy_over_product_lookup():
    """'can i return this bag' is about returns, not about bags."""
    reply = _ask("can i return this bag")
    assert reply["intent"] == "return_policy", reply


def test_concierge_admits_when_it_does_not_know():
    reply = _ask("what is the meaning of life")
    assert reply["method"] == "fallback"
    assert reply["intent"] == "unknown"
    assert "show me bags" in reply["reply"] or "prices" in reply["reply"]


def test_concierge_handles_empty_input():
    r = client.post("/chatbot", json={"message": "   "}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["reply"]
