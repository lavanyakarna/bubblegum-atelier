import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["favorites"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
FAVORITES_PATH = os.path.join(DATA_DIR, "favorites.json")
PRODUCTS_PATH = os.path.join(DATA_DIR, "products.json")


class FavoriteRequest(BaseModel):
    customer: str
    product_id: str


def _load_favorites():
    if not os.path.exists(FAVORITES_PATH):
        return {}
    with open(FAVORITES_PATH) as f:
        return json.load(f)


def _save_favorites(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FAVORITES_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _load_products():
    with open(PRODUCTS_PATH) as f:
        return json.load(f)["products"]


@router.post("/favorites")
def add_favorite(payload: FavoriteRequest):
    products = _load_products()
    if not any(p["id"] == payload.product_id for p in products):
        raise HTTPException(status_code=404, detail="Product not found")

    favorites = _load_favorites()
    customer_favs = favorites.setdefault(payload.customer, [])
    if payload.product_id not in customer_favs:
        customer_favs.append(payload.product_id)
    _save_favorites(favorites)
    return {"status": "ok", "customer": payload.customer, "favorites": customer_favs}


@router.delete("/favorites")
def remove_favorite(payload: FavoriteRequest):
    favorites = _load_favorites()
    customer_favs = favorites.get(payload.customer, [])
    if payload.product_id in customer_favs:
        customer_favs.remove(payload.product_id)
    favorites[payload.customer] = customer_favs
    _save_favorites(favorites)
    return {"status": "ok", "customer": payload.customer, "favorites": customer_favs}


@router.get("/favorites/{customer}")
def get_favorites(customer: str):
    favorites = _load_favorites()
    fav_ids = favorites.get(customer, [])
    products = _load_products()
    fav_products = [p for p in products if p["id"] in fav_ids]
    return {"customer": customer, "products": fav_products, "count": len(fav_products)}