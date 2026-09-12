# 🫧 Bubblegum Atelier

**An AI-assisted boutique storefront — full-stack, containerized, and live on the internet.**

🌐 **Storefront:** https://bubblegum-atelier.netlify.app
⚙️ **API:** https://bubblegum-atelier.onrender.com · **Interactive docs:** [/docs](https://bubblegum-atelier.onrender.com/docs)

> ⏳ The API runs on a free tier that naps when idle. A keep-alive workflow in this repo
> pings it every few minutes so the first visitor never meets a cold start.

---

## What it is

Bubblegum Atelier is a women's fashion boutique built as a real, deployed product rather than a notebook demo. Shoppers get a polished storefront — 87 products with consistent studio photography, live search, wishlists, a shopping bag, a concierge chatbot, and a **Style Wall** where customers post photos of what they bought and talk to each other about it. Behind the glass, a FastAPI backend runs trained machine-learning services for sentiment and image classification, plus an event pipeline that feeds the owner a live view of what the boutique is doing.

Everything ships through a containerized pipeline: tests and a Docker build gate every push, the storefront is served from Netlify's CDN, and the API runs from a Docker image on Render.

---

## ✨ Features

### The storefront
- **87 products across 7 categories** — shoes, bags, dresses, tops, bottoms, accessories, makeup (₹349–₹2,999)
- Cohesive AI-generated lookbook photography — one studio look across the whole catalogue
- **Live search** (name + category aware) and one-tap category chips
- **Zoom modal** — open any product, zoom and pan to inspect the detail, pick a size
- **Wishlist** (hearts) and **shopping bag** with quantity controls
- **Checkout intent** flow that records an order intent and clears the bag
- **Lookbook** — curated head-to-toe outfits, each with a **like button** and an "Add whole look" that drops the entire fit in your bag
- **Concierge chatbot** — answers about hours, shipping, returns, **and your actual products**

### 🌸 The Style Wall
The community corner of the boutique — and the place where the ML stops being invisible.

- **Share a look** — upload a photo of what you bought, give it 1–5 stars, add a caption, optionally tag the product
- **The studio reads it for you**: the vision model tags the photo ("Recognized: shoes") and the sentiment model reads your words ("Loved It")
- **Cheer** other shoppers' posts — one tap, one per person, tap again to take it back
- **Comment** on any post and reply to each other
- Newest first, with a live strip: looks shared, average rating, total cheers
- Every post, cheer and comment also lands in the event log, feeding the owner's analytics

### For You (recommendations)
- Picks driven by real behaviour — what you heart, what's in your bag, what you've already seen
- **Explains itself**: each suggestion carries a plain-language reason ("Because you wishlisted …")

### Owner dashboard
- **Overview** — visits, unique customers and the sentiment mix of reviews
- **Live funnel** — view → bag → wishlist → checkout → purchase, computed from the real event log
- **AI Insights** — written from your actual data on every page load, not sample text:
  *"Shoes draw the most attention — 328 views, about 17% of everything browsed"*
- **Clickable stat cards** — Total Visits, Unique Customers, Products Tagged and Concierge Chats each open a drill-down panel:
  - 7-day activity chart, views by category, most-viewed pieces with photos
  - the visitor list (guest ids masked, returning visitors flagged)
  - every photo the vision model has read, with confidence
  - real concierge questions and answers

### Identity
- Name + secret-word sign-in (`/identity/register`, `/identity/login`) with returning-customer handling
- Duplicate-name registration returns suggestions instead of failing silently

---

## 🧠 The machine-learning services

| Service | Under the hood | Where it lives |
|---|---|---|
| **Customer Mood** | scikit-learn — TF-IDF + logistic regression over the review corpus | `app/services/nlp_service.py` |
| **Product Studio** | TensorFlow / Keras — MobileNetV2 transfer learning | `app/services/cv_service.py` |
| **Boutique Concierge** | Whole-word rule matching + TF-IDF/logistic-regression intent model, with **live catalogue lookups** | `app/services/chatbot_service.py` |

Sentiment and chatbot models are **retrained in CI on every push**, so the pipeline proves the models can be built from raw data — not just loaded from a stale file.

### Where the machine learning actually shows up

| Surface | Model | What the user sees |
|---|---|---|
| Style Wall — uploaded photo | MobileNetV2 classifier | "✨ Recognized: bags" chip on the post |
| Style Wall — caption | Sentiment model | "Loved It" / "Mixed Feelings" / "Needs Love" chip |
| Concierge | Intent model + catalogue | Real prices, sizes and stock, e.g. *"Sugar Rush Platform Heels is INR 2499 and in stock. Sizes: 5, 6, 7, 8"* |
| Customer Mood page | Sentiment model | Mood + confidence for any pasted text |
| `POST /classify-product` | MobileNetV2 classifier | Category + confidence, straight from the API |

Two honesty rules are built in:
- the mood label is **hidden** when the model is under 0.5 confidence or contradicts the star rating
- the concierge **says it doesn't know** rather than inventing an answer, and offers what it can help with

Adding rows to `data/reviews.csv` or `data/intents.json` improves the models automatically — CI retrains on every push.

---

## ⚡ Performance

| | Before | Now |
|---|---|---|
| 4 decorative images | 4,410 KB | **148 KB** |
| Product photos | all 87 at once | **lazy-loaded** — only what's on screen |
| First visit total | ~9,500 KB | **~730 KB** |
| API response (warm) | — | **~0.08 s** |
| Cold start | 30–60 s | **prevented** by the keep-alive workflow |

The four oversized graphics were 1254×1254 PNGs displayed at 170–320 px. Re-encoded to
display-appropriate JPEGs, which I compared pixel-by-pixel against the originals — the
differences are imperceptible (mean pixel difference under 1.2/255).

---

## 🛠️ Tech stack

**Backend** — FastAPI · Uvicorn · Pydantic · JSON storage + append-only event log
**ML** — scikit-learn · TensorFlow/Keras · OpenCV · NumPy · pandas · joblib
**Frontend** — React 18 (in-browser Babel, single-file SPA, no build step) · custom CSS design system
**Quality** — pytest (34 tests) · data-isolating `conftest.py` · GitHub Actions (retrain → test → Docker build on every push)
**Infra** — Docker (python:3.11-slim + OpenCV runtime deps) · Netlify (CDN) · Render (API) · GitHub Actions keep-alive

---

## 🏗️ Architecture

```
        Browser  (React SPA — single HTML file)
               │  HTTPS, X-API-Key header
               ▼
   ┌── Netlify CDN ──┐          ┌─────────── Render (Docker) ───────────┐
   │  public/        │  REST    │  FastAPI                              │
   │  index.html     │ ───────▶ │   ├─ routers/  (35 endpoints)         │
   └─────────────────┘          │   │   products · cart · favorites ·   │
                                │   │   reviews · recommendations ·     │
   GitHub Actions               │   │   events · funnel · identity ·    │
    ├─ keep-alive ping (5 min)  │   │   nlp · chatbot · vision ·        │
    ├─ retrain ML models        │   │   stylewall · insights · lookbook │
    ├─ pytest  (34 tests)       │   ├─ services/  nlp · cv · chatbot     │
    └─ docker build             │   ├─ models/    .h5 · .pkl            │
        on every push           │   └─ data/      products.json ·        │
                                │                 events.jsonl ·         │
                                │                 stylewall.json + photos│
                                └───────────────────────────────────────┘
```

---

## 📡 API reference

All data endpoints require the header `X-API-Key`. Interactive docs: `/docs`.

| Group | Endpoints |
|---|---|
| Products | `GET /products` · `GET /products/{id}` |
| Cart | `GET /cart` · `POST /cart` · `PATCH /cart/{product_id}` · `DELETE /cart/{product_id}` · `POST /checkout-intent` |
| Wishlist | `POST /favorites` · `DELETE /favorites` · `GET /favorites/{customer}` |
| Reviews | `POST /reviews` (auto sentiment) · `GET /reviews` |
| Lookbook | `GET /lookbook/likes` · `POST /lookbook/{look_id}/like` |
| Styling | `GET /complete-the-look/{product_id}` |
| Events & funnel | `POST /events` · `GET /events/count` · `GET /funnel` |
| Identity | `POST /identity/register` · `POST /identity/login` |
| NLP | `POST /analyze-sentiment` |
| Chatbot | `POST /chatbot` |
| Vision | `POST /classify-product` |
| **Style Wall** | `POST /stylewall/posts` · `GET /stylewall/posts` · `POST /stylewall/posts/{id}/cheer` · `POST /stylewall/posts/{id}/comments` · `GET /stylewall/summary` |
| **Insights** | `GET /insights` · `GET /insights/visits` · `GET /insights/customers` · `GET /insights/chats` · `GET /insights/tagged` |
| Admin | `GET /` · `GET /dashboard/stats` |

### Style Wall in detail

```
POST /stylewall/posts           multipart: photo, rating (1-5), caption, customer, product_id?
                                → 201 with photo_url, cv_tag, sentiment, counts
GET  /stylewall/posts           ?limit=60&customer=<id>&rating=<1-5>  → newest first
POST /stylewall/posts/{id}/cheer     { customer }  → toggles; returns cheered + cheer_count
POST /stylewall/posts/{id}/comments  { customer, text } → 201 comment
GET  /stylewall/summary         posts, cheers, comments, average_rating, tagged_categories
```

Uploads are capped at 8 MB, re-encoded server-side to at most 900 px per side, and stored
as JPEGs under `data/stylewall/` (served at `/static/stylewall/…`). Post metadata lives in
`data/stylewall.json`, written via temp-file + atomic replace so a crash can't corrupt it.

---

## 🚀 Run it locally

```bash
# 1. install
pip install -r requirements.txt

# 2. (re)train the models from raw data — optional, artifacts are committed
python -m app.services.nlp_service
python -m app.services.chatbot_service

# 3. serve the API
uvicorn app.main:app --reload --port 8000
#    → http://127.0.0.1:8000/docs

# 4. the frontend is a single file — open public/index.html with any static server
#    (the API base URL is set near the top of the file)

# 5. tests
pytest tests/ -v
```

### Docker

```bash
docker build -t bubblegum-atelier .
docker run -p 8000:8000 bubblegum-atelier
```

---

## 🧪 Testing

`tests/test_endpoints.py` holds **34 end-to-end tests** covering: products and API-key
rejection, sentiment, chatbot quality (including a regression test proving the greeting
"hi" no longer matches inside "shipping"), dashboard stats, the cart flow, the identity
flow, the Style Wall (auth, validation, upload → feed, cheers, comments, 404s, summary),
the insights endpoints, lookbook likes, and guards proving removed features stay removed.

`tests/conftest.py` **snapshots `data/` before the suite runs and restores it afterwards**,
so testing never leaves test posts on the live wall or test rows in the event log.

```bash
pytest tests/ -v      # 34 passed
```

CI (`.github/workflows/deploy.yml`) retrains the models, runs the suite, and builds the
Docker image on every push to `main`. A second workflow keeps the hosted API awake.

---

## 📁 Project layout

```
app/
  main.py              FastAPI app — middleware, routers, dashboard
  routers/             14 routers, 35 endpoints
  services/            nlp_service · cv_service · chatbot_service
  models/              sentiment .pkl · vectorizer .pkl · chatbot .pkl · MobileNetV2 .h5
  storage.py           atomic JSON writes + append-only event log
data/
  products.json        the 87-product catalogue
  reviews.json/.csv    customer feedback + sentiment training corpus
  intents.json         concierge training data (30 intents, 214 phrases)
  favorites.json       wishlists
  carts.json           shopping bags
  events.jsonl         append-only analytics stream
  stylewall.json       Style Wall posts
  stylewall/           uploaded shopper photos
  chats.json           concierge conversations
  lookbook_likes.json  outfit likes
  products/ graphics/  lookbook and UI imagery
public/index.html      the deployed storefront
frontend/index.html    development copy of the SPA
tests/                 pytest suite + data isolation
.github/workflows/     CI (retrain → test → docker) and keep-alive
Dockerfile             python:3.11-slim, uvicorn, port 8000
```

---

## 🚧 Roadmap

- Persistent uploads (S3/Cloudinary) so the Style Wall and likes survive a redeploy
- Grow `data/reviews.csv` and `data/intents.json` to sharpen the models
- Move JSON files to Postgres and the event stream to a managed store
- Loyalty + membership card on the shopper profile
- Payments (sandbox) behind the checkout intent

---

Built by **Lavanya Karna** — [github.com/lavanyakarna](https://github.com/lavanyakarna)
