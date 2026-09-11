import os
import csv
from collections import Counter

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import vision, nlp, chatbot, products
from app.routers import favorites, reviews, recommendations
from app.routers import events
from app.routers import cart
from app.routers import identity

API_KEY = os.environ.get("RETAIL_API_KEY", "dev-key-123")

app = FastAPI(
    title="Bubblegum Atelier — Boutique Intelligence Platform",
    description="Face recognition (Customer Memory), product classification (Product Studio), sentiment analysis (Customer Mood), and FAQ chatbot (Boutique Concierge) behind one API.",
    version="1.0.0",
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

@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}


@app.get("/dashboard/stats", dependencies=[Depends(verify_api_key)])
def dashboard_stats():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    visits_path = os.path.join(data_dir, "customer_visits.csv")

    total_visits, customers = 0, set()
    if os.path.exists(visits_path):
        with open(visits_path) as f:
            for row in csv.DictReader(f):
                total_visits += 1
                customers.add(row["customer"])

    return {
        "total_visits": total_visits,
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