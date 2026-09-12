"""
Style Wall — shoppers share photos of what they bought, and the community cheers
and comments on them. Two of the boutique's ML brains run on every post:

    photo   -> vision model tags the garment category   ("Recognized: bags")
    caption -> sentiment model reads the mood           ("Loved It")

Every classification is also written to the event log, so the owner dashboard can
show a real "Products Tagged" count instead of a session counter.

Storage is deliberately simple and matches the rest of the project: metadata in
one JSON file, photos as JPEGs on disk under data/stylewall/ (which main.py
already serves at /static).
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.routers.nlp import get_sentiment_service
from app.services.cv_service import ProductClassifierService
from app.storage import append_event

router = APIRouter(prefix="/stylewall", tags=["stylewall"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
POSTS_PATH = os.path.join(DATA_DIR, "stylewall.json")
PHOTO_DIR = os.path.join(DATA_DIR, "stylewall")

MAX_UPLOAD_BYTES = 8 * 1024 * 1024   # 8 MB ceiling on uploads
MAX_PHOTO_SIDE = 900                 # we re-encode down to this before storing
JPEG_QUALITY = 82

_classifier = None


def get_classifier() -> ProductClassifierService:
    """Lazy singleton - loading the vision model takes a moment."""
    global _classifier
    if _classifier is None:
        _classifier = ProductClassifierService()
    return _classifier


# --------------------------------------------------------------------------- storage

def _load_posts() -> list:
    if not os.path.exists(POSTS_PATH):
        return []
    try:
        with open(POSTS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_posts(posts: list) -> None:
    """Write via a temp file + atomic replace so a crash can't corrupt the wall."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = POSTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)
    os.replace(tmp, POSTS_PATH)


def _find_post(posts: list, post_id: str) -> dict:
    for p in posts:
        if p["id"] == post_id:
            return p
    raise HTTPException(status_code=404, detail=f"No post with id '{post_id}'")


# --------------------------------------------------------------------------- helpers

def _decode_image(raw: bytes):
    arr = np.frombuffer(raw, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _store_photo(img) -> str:
    """Re-encode the upload to a sensibly sized JPEG and return its public URL."""
    h, w = img.shape[:2]
    if max(h, w) > MAX_PHOTO_SIDE:
        scale = MAX_PHOTO_SIDE / max(h, w)
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)

    os.makedirs(PHOTO_DIR, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}.jpg"
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise HTTPException(status_code=500, detail="Could not encode that photo.")

    with open(os.path.join(PHOTO_DIR, name), "wb") as f:
        f.write(buf.tobytes())
    return f"/static/stylewall/{name}"


def _read_mood(text: str) -> Optional[dict]:
    """Sentiment is a bonus, never a blocker: if the model isn't trained, skip it."""
    if not text or not text.strip():
        return None
    try:
        service = get_sentiment_service()
        return service.predict(text)
    except Exception:                                        # noqa: BLE001
        return None


def _read_category(img) -> Optional[dict]:
    """Same deal for vision: an untrained model must not break the wall."""
    try:
        result = get_classifier().predict(img)
    except Exception:                                        # noqa: BLE001
        return None
    if result.get("category"):
        return {"category": result["category"], "confidence": result.get("confidence")}
    return None


def _public_view(post: dict, viewer: Optional[str] = None) -> dict:
    """Shape a post for the client, including counts and whether *you* cheered."""
    cheers = post.get("cheers", []) or []
    comments = post.get("comments", []) or []
    return {
        "id": post["id"],
        "customer": post.get("customer") or "A guest",
        "caption": post.get("caption") or "",
        "rating": post.get("rating"),
        "product_id": post.get("product_id"),
        "photo_url": post.get("photo_url"),
        "cv_tag": post.get("cv_tag"),
        "sentiment": post.get("sentiment"),
        "timestamp": post.get("timestamp"),
        "cheer_count": len(cheers),
        "cheered": bool(viewer) and viewer in cheers,
        "comment_count": len(comments),
        "comments": comments,
    }


# --------------------------------------------------------------------------- models

class CheerRequest(BaseModel):
    customer: str


class CommentRequest(BaseModel):
    customer: str
    text: str


# --------------------------------------------------------------------------- routes

@router.post("/posts", status_code=201)
async def create_post(
    photo: UploadFile = File(...),
    rating: int = Form(...),
    caption: str = Form(""),
    customer: str = Form(""),
    product_id: str = Form(""),
):
    """Publish a photo of a purchase, with a star rating and an optional note."""
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5 stars.")

    raw = await photo.read()
    if not raw:
        raise HTTPException(status_code=400, detail="No photo was uploaded.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="That photo is larger than 8 MB - try a smaller one.")

    img = _decode_image(raw)
    if img is None:
        raise HTTPException(status_code=400, detail="That file didn't look like an image we can read.")

    cv_tag = _read_category(img)

    post = {
        "id": uuid.uuid4().hex[:10],
        "customer": (customer or "").strip() or "A guest",
        "caption": (caption or "").strip(),
        "rating": int(rating),
        "product_id": (product_id or "").strip() or None,
        "photo_url": _store_photo(img),
        "cv_tag": cv_tag,
        "sentiment": _read_mood(caption),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cheers": [],
        "comments": [],
    }

    posts = _load_posts()
    posts.append(post)
    _save_posts(posts)

    # let the owner dashboard count every photo the vision model has read
    if cv_tag:
        append_event({
            "customer_id": post["customer"],
            "type": "classify",
            "product_id": post["product_id"],
            "meta": {
                "category": cv_tag.get("category"),
                "confidence": cv_tag.get("confidence"),
                "source": "style_wall",
            },
        })

    return _public_view(post, viewer=post["customer"])


@router.get("/posts")
def list_posts(
    limit: int = Query(60, ge=1, le=200),
    customer: Optional[str] = Query(None),
    rating: Optional[int] = Query(None, ge=1, le=5),
):
    """Newest first. Pass ?customer=<id> to learn whether you've cheered each one."""
    posts = _load_posts()
    if rating is not None:
        posts = [p for p in posts if p.get("rating") == rating]
    posts = sorted(posts, key=lambda p: p.get("timestamp", ""), reverse=True)[:limit]
    return {"posts": [_public_view(p, viewer=customer) for p in posts], "count": len(posts)}


@router.post("/posts/{post_id}/cheer")
def toggle_cheer(post_id: str, payload: CheerRequest):
    """Tap the heart again to take it back."""
    posts = _load_posts()
    post = _find_post(posts, post_id)
    cheers = post.setdefault("cheers", [])

    if payload.customer in cheers:
        cheers.remove(payload.customer)
        cheered = False
    else:
        cheers.append(payload.customer)
        cheered = True

    _save_posts(posts)
    return {"post_id": post_id, "cheered": cheered, "cheer_count": len(cheers)}


@router.post("/posts/{post_id}/comments", status_code=201)
def add_comment(post_id: str, payload: CommentRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Comment can't be empty.")

    posts = _load_posts()
    post = _find_post(posts, post_id)

    comment = {
        "id": uuid.uuid4().hex[:8],
        "customer": payload.customer or "A guest",
        "text": payload.text.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    post.setdefault("comments", []).append(comment)
    _save_posts(posts)
    return comment


@router.get("/summary")
def summary():
    """Small rollup for the owner's dashboard."""
    posts = _load_posts()
    if not posts:
        return {"posts": 0, "cheers": 0, "comments": 0, "average_rating": None, "tagged_categories": {}}

    ratings = [p.get("rating") for p in posts if isinstance(p.get("rating"), int)]
    categories: dict = {}
    for p in posts:
        tag = p.get("cv_tag") or {}
        cat = tag.get("category")
        if cat:
            categories[cat] = categories.get(cat, 0) + 1

    return {
        "posts": len(posts),
        "cheers": sum(len(p.get("cheers", []) or []) for p in posts),
        "comments": sum(len(p.get("comments", []) or []) for p in posts),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "tagged_categories": categories,
    }
