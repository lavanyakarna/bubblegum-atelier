import os
import csv
import json
from collections import Counter

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import vision, nlp, chatbot, products
from app.routers import favorites, reviews, recommendations
from app.routers import events
from app.routers import cart
from app.routers import identity
from app.routers import stylewall

API_KEY = os.environ.get("RETAIL_API_KEY", "dev-key-123")

app = FastAPI(
    title="Bubblegum Atelier — Boutique Intelligence Platform",
    description="Product classification (Product Studio), sentiment analysis (Customer Mood), a FAQ chatbot (Boutique Concierge) and the shopper Style Wall behind one API.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# serve product images (and other files in data/) as static files
app.mount("/static", StaticFiles(directory="data"), name="static")


def verify_api_key(x_api_key: str = Header(default=None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")
    return True


app.include_router(vision.router, dependencies=[Depends(verify_api_key)])
app.include_router(nlp.router, dependencies=[Depends(verify_api_key)])
app.include_router(chatbot.router, dependencies=[Depends(verify_api_key)])
app.include_router(products.router, dependencies=[Depends(verify_api_key)])
app.include_router(favorites.router, dependencies=[Depends(verify_api_key)])
from app.routers import funnel
app.include_router(funnel.router, dependencies=[Depends(verify_api_key)])
app.include_router(reviews.router, dependencies=[Depends(verify_api_key)])
app.include_router(recommendations.router, dependencies=[Depends(verify_api_key)])
app.include_router(events.router, dependencies=[Depends(verify_api_key)])
app.include_router(cart.router, dependencies=[Depends(verify_api_key)])
app.include_router(identity.router, dependencies=[Depends(verify_api_key)])
app.include_router(stylewall.router, dependencies=[Depends(verify_api_key)])


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}


@app.get("/dashboard/stats", dependencies=[Depends(verify_api_key)])
def dashboard_stats():
    """Live numbers, read straight from the real event log."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    events_path = os.path.join(data_dir, "events.jsonl")

    views, customers = 0, set()
    if os.path.exists(events_path):
        with open(events_path, encoding="utf-8") as f:
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
                if entry.get("type") == "view":
                    views += 1
                cid = entry.get("customer_id")
                if cid and cid != "anonymous":
                    customers.add(cid)

    return {
        "total_visits": views,
        "unique_customers": len(customers),
        "sentiment_breakdown": {},
    }


from fastapi.responses import JSONResponse
from fastapi.requests import Request
import traceback

@app.exception_handler(Exception)
async def catch_all_exceptions(request: Request, exc: Exception):
    print("=" * 60)
    print(f"UNHANDLED ERROR on {request.url}")
    traceback.print_exc()
    print("=" * 60)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
        headers={"Access-Control-Allow-Origin": "*"},
    )
