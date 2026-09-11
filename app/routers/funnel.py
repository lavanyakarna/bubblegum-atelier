import json
import os
from fastapi import APIRouter

router = APIRouter(tags=["funnel"])

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVENTS_PATH = os.path.join(BASE, "data", "events.jsonl")

STAGES = [
    ("view", "Viewed products"),
    ("cart_add", "Added to bag"),
    ("wishlist_add", "Wishlisted"),
    ("checkout_intent", "Started checkout"),
    ("purchase", "Purchased"),
]


def _load_counts():
    """Count every real event in events.jsonl. Tolerant of old/odd lines."""
    counts = {}
    if not os.path.exists(EVENTS_PATH):
        return counts
    with open(EVENTS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            etype = entry.get("type") or entry.get("event")
            if etype == "wishlist":
                etype = "wishlist_add"
            if etype:
                counts[etype] = counts.get(etype, 0) + 1
    return counts


@router.get("/funnel")
def funnel():
    counts = _load_counts()
    first_stage = counts.get("view", 0)
    stages = []
    for key, label in STAGES:
        c = counts.get(key, 0)
        stages.append({
            "key": key,
            "label": label,
            "count": c,
            "pct": round(c / first_stage * 100, 1) if first_stage else 0,
        })
    return {
        "stages": stages,
        "pending_carts": max(0, counts.get("cart_add", 0) - counts.get("checkout_intent", 0)),
        "total_events": sum(counts.values()),
    }
