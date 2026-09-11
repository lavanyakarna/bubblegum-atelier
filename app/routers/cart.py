from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.storage import read_json, write_json, append_event

router = APIRouter(tags=["cart"])

CARTS_FILE = "carts.json"
PRODUCTS_FILE = "products.json"
ORDERS_FILE = "order_intents.json"


class AddToCart(BaseModel):
    product_id: str
    qty: int = 1


class UpdateQty(BaseModel):
    qty: int


def _load_products():
    data = read_json(PRODUCTS_FILE, {"products": []})
    return {p["id"]: p for p in data["products"]}


def _get_cart(customer_id: str):
    carts = read_json(CARTS_FILE, {})
    return carts.get(customer_id, {})


def _save_cart(customer_id: str, cart: dict):
    carts = read_json(CARTS_FILE, {})
    if cart:
        carts[customer_id] = cart
    else:
        carts.pop(customer_id, None)
    write_json(CARTS_FILE, carts)


def _cart_response(customer_id: str):
    """Cart with product details joined in and totals computed SERVER-side."""
    products = _load_products()
    cart = _get_cart(customer_id)
    items, total = [], 0.0
    for product_id, qty in cart.items():
        product = products.get(product_id)
        if not product:
            continue
        line_total = round(product["price"] * qty, 2)
        total += line_total
        items.append({"product": product, "qty": qty, "line_total": line_total})
    return {
        "customer": customer_id,
        "items": items,
        "item_count": sum(i["qty"] for i in items),
        "total": round(total, 2),
    }


@router.get("/cart")
def get_cart(x_customer_id: str = Header(default="anonymous")):
    return _cart_response(x_customer_id)


@router.post("/cart", status_code=201)
def add_to_cart(body: AddToCart, x_customer_id: str = Header(default="anonymous")):
    products = _load_products()
    product = products.get(body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.get("in_stock", True):
        raise HTTPException(status_code=400, detail="Product is out of stock")
    if body.qty < 1:
        raise HTTPException(status_code=400, detail="qty must be 1 or more")

    cart = _get_cart(x_customer_id)
    cart[body.product_id] = cart.get(body.product_id, 0) + body.qty
    _save_cart(x_customer_id, cart)
    append_event({"customer_id": x_customer_id, "type": "cart_add",
                  "product_id": body.product_id, "meta": {"qty": body.qty}})
    return _cart_response(x_customer_id)


@router.patch("/cart/{product_id}")
def update_qty(product_id: str, body: UpdateQty, x_customer_id: str = Header(default="anonymous")):
    cart = _get_cart(x_customer_id)
    if product_id not in cart:
        raise HTTPException(status_code=404, detail="Product not in cart")
    if body.qty < 0:
        raise HTTPException(status_code=400, detail="qty cannot be negative")
    if body.qty == 0:
        cart.pop(product_id)
    else:
        cart[product_id] = body.qty
    _save_cart(x_customer_id, cart)
    append_event({"customer_id": x_customer_id, "type": "cart_update",
                  "product_id": product_id, "meta": {"qty": body.qty}})
    return _cart_response(x_customer_id)


@router.delete("/cart/{product_id}")
def remove_from_cart(product_id: str, x_customer_id: str = Header(default="anonymous")):
    cart = _get_cart(x_customer_id)
    if product_id not in cart:
        raise HTTPException(status_code=404, detail="Product not in cart")
    cart.pop(product_id)
    _save_cart(x_customer_id, cart)
    append_event({"customer_id": x_customer_id, "type": "cart_remove",
                  "product_id": product_id, "meta": {}})
    return _cart_response(x_customer_id)


@router.post("/checkout-intent", status_code=201)
def checkout_intent(x_customer_id: str = Header(default="anonymous")):
    cart = _get_cart(x_customer_id)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    summary = _cart_response(x_customer_id)
    append_event({"customer_id": x_customer_id, "type": "checkout_intent",
                  "product_id": None,
                  "meta": {"item_count": summary["item_count"], "total": summary["total"]}})

    orders = read_json(ORDERS_FILE, [])
    order = {
        "id": f"order-{len(orders) + 1:04d}",
        "customer_id": x_customer_id,
        "items": [{"product_id": i["product"]["id"], "qty": i["qty"], "line_total": i["line_total"]}
                  for i in summary["items"]],
        "item_count": summary["item_count"],
        "total": summary["total"],
    }
    orders.append(order)
    write_json(ORDERS_FILE, orders)

    _save_cart(x_customer_id, {})  # cart clears after intent is recorded
    return {
        "order_intent_id": order["id"],
        "item_count": order["item_count"],
        "total": order["total"],
        "message": "Order intent recorded (demo storefront - no payment taken)",
    }