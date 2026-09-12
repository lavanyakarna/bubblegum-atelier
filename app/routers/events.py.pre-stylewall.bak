from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.storage import append_event, read_events

router = APIRouter(tags=["events"])

# event types that feed our funnel + personalization (kept small on purpose)
ALLOWED_TYPES = {
    "view", "search", "wishlist_add", "wishlist_remove",
    "cart_add", "cart_update", "cart_remove",
    "checkout_intent", "rec_click", "review",
}


class Event(BaseModel):
    type: str
    product_id: Optional[str] = None
    meta: Optional[dict] = None


@router.post("/events", status_code=201)
def create_event(event: Event, x_customer_id: str = Header(default="anonymous")):
    if event.type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"unknown event type: {event.type}")
    append_event({
        "customer_id": x_customer_id,
        "type": event.type,
        "product_id": event.product_id,
        "meta": event.meta or {},
    })
    return {"ok": True}


@router.get("/events/count")
def events_count():
    return {"events": len(read_events())}