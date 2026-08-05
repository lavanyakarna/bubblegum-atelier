import json
import os
from fastapi import APIRouter, Query
from typing import Optional
from app.schemas import ProductListResponse

router = APIRouter(tags=["products"])

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "products.json")


def load_products():
    with open(DATA_PATH) as f:
        return json.load(f)["products"]


@router.get("/products", response_model=ProductListResponse)
def get_products(category: Optional[str] = Query(None), in_stock_only: bool = False):
    products = load_products()
    if category:
        products = [p for p in products if p["category"] == category]
    if in_stock_only:
        products = [p for p in products if p["in_stock"]]
    return {"products": products, "count": len(products)}


@router.get("/products/{product_id}")
def get_product(product_id: str):
    products = load_products()
    for p in products:
        if p["id"] == product_id:
            return p
    return {"error": "not_found"}