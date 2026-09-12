"""
Insights — the owner dashboard's real numbers.

Everything here is computed from data the boutique already records:

    data/events.jsonl    every view, bag add, checkout, chat, classification, like
    data/products.json   the catalogue (names + categories)
    data/reviews.json    customer reviews and their sentiment
    data/stylewall.json  shopper posts, ratings, ML tags
    data/chats.json      concierge conversations

No sample text, no made-up numbers: if the boutique hasn't done something yet,
the endpoint says so instead of inventing an observation.
"""

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.storage import read_events, read_json

router = APIRouter(prefix="/insights", tags=["insights"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PRODUCTS_PATH = os.path.join(BASE_DIR, "data", "products.json")


# --------------------------------------------------------------------------- helpers

def _products():
    """id -> product, so we can turn a product_id into a name/category/price."""
    try:
        with open(PRODUCTS_PATH, encoding="utf-8") as f:
            return {p["id"]: p for p in json.load(f).get("products", [])}
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return {}


def _ts(value):
    """Parse a stored timestamp; returns None when it's missing or odd."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _mask(customer_id: str) -> str:
    """Guests are anonymous here - never show a raw id on the dashboard."""
    if not customer_id or customer_id == "anonymous":
        return "A visitor"
    if customer_id.startswith("guest-"):
        return "Guest " + customer_id[6:10]
    if customer_id.startswith("pytest"):
        return "Automated test"
    if len(customer_id) > 18:            # a generated id, not a name
        return customer_id[:8] + "..."
    return customer_id


def _views(events):
    return [e for e in events if e.get("type") == "view" and e.get("product_id")]


def _by_type(events, kind):
    return [e for e in events if e.get("type") == kind]


# --------------------------------------------------------------------------- overview

@router.get("")
def insights():
    """The cards on the dashboard - written from what actually happened."""
    events = read_events()
    products = _products()
    reviews = read_json("reviews.json", [])
    wall = read_json("stylewall.json", [])

    views = _views(events)
    carts = _by_type(events, "cart_add")
    wishlists = _by_type(events, "wishlist_add")
    checkouts = _by_type(events, "checkout_intent")
    chats = read_json("chats.json", [])
    classified = _by_type(events, "classify")

    customers = {e.get("customer_id") for e in events
                 if e.get("customer_id") and e.get("customer_id") != "anonymous"}

    cards = []

    # --- what shoppers looked at -------------------------------------------------
    if views:
        cat_counts, prod_counts = Counter(), Counter()
        for e in views:
            pid = e.get("product_id")
            prod_counts[pid] += 1
            p = products.get(pid)
            if p:
                cat_counts[p.get("category", "other")] += 1

        if cat_counts:
            cat, n = cat_counts.most_common(1)[0]
            share = round(n / max(1, sum(cat_counts.values())) * 100)
            cards.append({
                "icon": "hanger",
                "title": f"{cat.title()} draw the most attention",
                "text": f"{n} views on {cat} - about {share}% of everything shoppers browsed.",
            })

        if prod_counts:
            pid, n = prod_counts.most_common(1)[0]
            p = products.get(pid)
            if p:
                cards.append({
                    "icon": "star",
                    "title": f"'{p['name']}' is the most-viewed piece",
                    "text": f"{n} views so far, listed at {p.get('currency', 'INR')} {p.get('price')}.",
                })

    # --- how far shoppers get ----------------------------------------------------
    if views:
        rate = len(carts) / len(views) * 100
        cards.append({
            "icon": "bolt",
            "title": f"{rate:.1f}% of product views become bag adds",
            "text": f"{len(carts)} bag adds from {len(views)} views. Checkout started {len(checkouts)} times.",
        })
    if wishlists:
        cards.append({
            "icon": "heart",
            "title": f"{len(wishlists)} items saved to wishlists",
            "text": "Wishlisted pieces are your warmest audience - they came back for them.",
        })

    # --- what customers said -----------------------------------------------------
    if reviews:
        moods = Counter(r.get("sentiment") for r in reviews if r.get("sentiment"))
        total = sum(moods.values())
        loved = moods.get("positive", 0)
        if total:
            cards.append({
                "icon": "chat",
                "title": f"{round(loved / total * 100)}% of reviews are loved",
                "text": f"{total} reviews read by the mood model: {loved} positive, "
                        f"{moods.get('neutral', 0)} mixed, {moods.get('negative', 0)} needing attention.",
            })

    # --- the Style Wall ----------------------------------------------------------
    if wall:
        ratings = [p.get("rating") for p in wall if isinstance(p.get("rating"), int)]
        tags = Counter((p.get("cv_tag") or {}).get("category") for p in wall)
        tags.pop(None, None)
        avg = round(sum(ratings) / len(ratings), 1) if ratings else None
        if tags:
            top_tag, top_n = tags.most_common(1)[0]
            cards.append({
                "icon": "camera",
                "title": f"Style Wall photos mostly read as {top_tag}",
                "text": f"{len(wall)} looks shared"
                        + (f", averaging {avg} stars" if avg else "")
                        + f"; the vision model tagged {top_n} of them as {top_tag}.",
            })
        else:
            cards.append({
                "icon": "camera",
                "title": f"{len(wall)} looks shared on the Style Wall",
                "text": (f"Averaging {avg} stars." if avg else "No ratings yet."),
            })

    # --- concierge ---------------------------------------------------------------
    if chats:
        intents = Counter(c.get("intent") for c in chats if c.get("intent"))
        if intents:
            top_intent, n = intents.most_common(1)[0]
            cards.append({
                "icon": "chat",
                "title": f"Most-asked topic: {top_intent}",
                "text": f"{len(chats)} conversations so far; {n} of them were about {top_intent}.",
            })
        else:
            cards.append({
                "icon": "chat",
                "title": f"{len(chats)} concierge conversations",
                "text": "Your shoppers are asking questions - worth a look.",
            })

    # --- when the boutique is busiest --------------------------------------------
    hours = Counter()
    for e in events:
        t = _ts(e.get("ts"))
        if t:
            hours[t.hour] += 1
    if hours:
        hour, n = hours.most_common(1)[0]
        label = f"{hour:02d}:00-{(hour + 1) % 24:02d}:00"
        cards.append({
            "icon": "bolt",
            "title": f"Busiest hour: {label}",
            "text": f"{n} of your {len(events)} recorded actions happened in this hour.",
        })

    if not cards:
        cards.append({
            "icon": "flower",
            "title": "Your boutique is just getting started",
            "text": "Insights appear here as soon as shoppers begin browsing, bagging and chatting.",
        })

    return {
        "insights": cards[:6],
        "totals": {
            "visits": len(views),
            "customers": len(customers),
            "tagged": len(classified),
            "chats": len(chats),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events_considered": len(events),
    }


# --------------------------------------------------------------------------- drill-downs

@router.get("/visits")
def visits():
    """What people looked at, and when."""
    events = read_events()
    products = _products()
    views = _views(events)

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    last_24h = sum(1 for e in views if (_ts(e.get("ts")) or now) >= day_ago)

    # last 7 days of activity
    days = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        count = sum(1 for e in views if (_ts(e.get("ts")) or now).date() == day)
        days.append({"date": day.isoformat(), "label": day.strftime("%a"), "count": count})

    product_counts = Counter(e.get("product_id") for e in views)
    top_products = []
    for pid, n in product_counts.most_common(8):
        p = products.get(pid, {})
        top_products.append({
            "id": pid,
            "name": p.get("name", pid),
            "category": p.get("category", "unknown"),
            "price": p.get("price"),
            "views": n,
            "image": p.get("image"),
        })

    cat_counts = Counter()
    for pid, n in product_counts.items():
        p = products.get(pid)
        if p:
            cat_counts[p.get("category", "other")] += n
    top_categories = [{"category": c, "views": n} for c, n in cat_counts.most_common(8)]

    return {
        "total": len(views),
        "last_24h": last_24h,
        "busiest_day": max(days, key=lambda d: d["count"]) if days else None,
        "days": days,
        "top_products": top_products,
        "top_categories": top_categories,
    }


@router.get("/customers")
def customers():
    """Who has been visiting - anonymous guest ids, never personal data."""
    events = read_events()
    seen = {}
    for e in events:
        cid = e.get("customer_id")
        if not cid or cid == "anonymous":
            continue
        t = _ts(e.get("ts"))
        entry = seen.setdefault(cid, {"id": cid, "events": 0, "first_seen": None, "last_seen": None})
        entry["events"] += 1
        if t:
            if entry["first_seen"] is None or t < entry["first_seen"]:
                entry["first_seen"] = t
            if entry["last_seen"] is None or t > entry["last_seen"]:
                entry["last_seen"] = t

    people = []
    for cid, entry in seen.items():
        people.append({
            "id": cid,
            "label": _mask(cid),
            "events": entry["events"],
            "first_seen": entry["first_seen"].isoformat() if entry["first_seen"] else None,
            "last_seen": entry["last_seen"].isoformat() if entry["last_seen"] else None,
            "returning": (entry["last_seen"] - entry["first_seen"]).total_seconds() > 1800
            if entry["first_seen"] and entry["last_seen"] else False,
        })

    people.sort(key=lambda p: p["events"], reverse=True)

    return {
        "total": len(people),
        "returning": sum(1 for p in people if p["returning"]),
        "customers": people[:25],
    }


@router.get("/chats")
def chats():
    """Recent concierge conversations."""
    stored = read_json("chats.json", [])
    recent = list(reversed(stored[-25:]))
    return {
        "total": len(stored),
        "recent": recent,
    }


@router.get("/tagged")
def tagged():
    """Every photo the vision model has read, newest first."""
    events = read_events()
    classified = [e for e in events if e.get("type") == "classify"]

    recent = []
    for e in sorted(classified, key=lambda x: str(x.get("ts") or ""), reverse=True)[:25]:
        meta = e.get("meta") or {}
        recent.append({
            "category": meta.get("category"),
            "confidence": meta.get("confidence"),
            "source": meta.get("source", "vision"),
            "product_id": e.get("product_id"),
            "ts": e.get("ts"),
        })

    counts = Counter((e.get("meta") or {}).get("category") for e in classified)
    counts.pop(None, None)

    return {
        "total": len(classified),
        "by_category": [{"category": c, "count": n} for c, n in counts.most_common()],
        "recent": recent,
    }
