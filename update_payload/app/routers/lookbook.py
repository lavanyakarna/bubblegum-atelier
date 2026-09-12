"""
Lookbook — likes for the curated outfits.

The looks themselves live in the frontend (they're a styling choice, not data),
so this router only remembers *who liked what*:

    data/lookbook_likes.json    { "look-1": ["guest-abc", "Lavanya"], ... }

Same storage helper the rest of the project uses, so writes are atomic.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage import append_event, read_json, write_json

router = APIRouter(prefix="/lookbook", tags=["lookbook"])

LIKES_FILE = "lookbook_likes.json"
MAX_LOOKS = 200   # sanity ceiling so a bad request can't bloat the file


class LikeRequest(BaseModel):
    customer: str


def _load():
    data = read_json(LIKES_FILE, {})
    return data if isinstance(data, dict) else {}


@router.get("/likes")
def list_likes(customer: str = ""):
    """Every look's like count, plus whether *you* liked it."""
    likes = _load()
    looks = {}
    for look_id, people in likes.items():
        people = people or []
        looks[look_id] = {
            "count": len(people),
            "liked": bool(customer) and customer in people,
        }
    total = sum(v["count"] for v in looks.values())
    ranked = sorted(looks.items(), key=lambda kv: kv[1]["count"], reverse=True)
    return {
        "looks": looks,
        "total_likes": total,
        "most_loved": [{"look_id": lid, "count": v["count"]} for lid, v in ranked if v["count"] > 0][:5],
    }


@router.post("/{look_id}/like")
def toggle_like(look_id: str, payload: LikeRequest):
    """Like a look, or take the like back - one per customer."""
    if not look_id or len(look_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid look id.")
    if not payload.customer or not payload.customer.strip():
        raise HTTPException(status_code=400, detail="We need to know who is liking this.")

    customer = payload.customer.strip()[:80]
    likes = _load()
    people = likes.setdefault(look_id, [])

    if customer in people:
        people.remove(customer)
        liked = False
    else:
        people.append(customer)
        liked = True

    if len(likes) > MAX_LOOKS:
        raise HTTPException(status_code=400, detail="Too many look entries stored.")

    write_json(LIKES_FILE, likes)
    append_event({
        "customer_id": customer,
        "type": "look_like",
        "product_id": None,
        "meta": {"look_id": look_id, "liked": liked},
    })

    return {"look_id": look_id, "liked": liked, "like_count": len(people)}
