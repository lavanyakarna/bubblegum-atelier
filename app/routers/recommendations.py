import json
import os
import random
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["recommendations"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PRODUCTS_PATH = os.path.join(DATA_DIR, "products.json")


def _load_products():
    with open(PRODUCTS_PATH) as f:
        return json.load(f)["products"]


@router.get("/complete-the-look/{product_id}")
def complete_the_look(product_id: str):
    products = _load_products()
    anchor = next((p for p in products if p["id"] == product_id), None)
    if not anchor:
        raise HTTPException(status_code=404, detail="Product not found")

    other_categories = {}
    for p in products:
        if p["category"] == anchor["category"] or not p.get("in_stock", True):
            continue
        other_categories.setdefault(p["category"], []).append(p)

    suggestions = []
    for category, items in other_categories.items():
        suggestions.append(random.choice(items))

    return {"anchor": anchor, "suggestions": suggestions, "count": len(suggestions)}