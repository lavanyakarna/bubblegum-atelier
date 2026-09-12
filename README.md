# 🫧 Bubblegum Atelier

**An AI-assisted boutique storefront — full-stack, containerized, and live on the internet.**

🌐 **Storefront:** https://bubblegum-atelier.netlify.app
⚙️ **API:** https://bubblegum-atelier.onrender.com · **Interactive docs:** [/docs](https://bubblegum-atelier.onrender.com/docs)

> ⏳ The API runs on a free tier that naps when idle — the first request after a quiet spell can take up to a minute to wake it. Everything after that is instant.

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
- **Lookbook** page for browsing the collection editorially
- **Concierge chatbot** — ask about hours, returns, stock and shipping

### 🌸 The Style Wall
The community corner of the boutique — and the place where the ML stops being invisible.

- **Share a look** — upload a photo of what you bought, give it 1–5 stars, add a caption, optionally tag the product from the catalogue
- **The studio reads it for you**: the vision model tags the photo ("Recognized: shoes") and the sentiment model reads your words ("Loved It")
- **Cheer** other shoppers' posts — one tap, one per person, tap again to take it back
- **Comment** on any post and reply to each other
- Newest first, with a live strip: how many looks are shared, the average rating, and total cheers
- Every post, cheer and comment also lands in the event log, so the wall feeds the funnel/analytics

### For You (recommendations)
- Picks driven by real behaviour — what you heart, what's in your bag, and what you've already seen
- **Explains itself**: each suggestion carries a plain-language reason ("Because you wishlisted …")
- Recommendation views and interactions are recorded as events, so the effect of the rail is measurable rather than assumed
- Runs transparently against the catalogue on the client, so you can read exactly why a product was chosen — the API also exposes a `GET /complete-the-look/{product_id}` companion endpoint

### Owner view
- **Overview** — total visits, unique customers, session activity, and the sentiment mix from customer reviews
- **Customer Mood** — reads free-text feedback and labels it (Loved It / Mixed Feelings / Needs Attention) with confidence
- **Live funnel** — stages from visit → bag → checkout, computed from the real event log

### Identity
- Name + secret-word sign-in (`/identity/register`, `/identity/login`) with returning-customer handling
- Duplicate-name registration returns suggestions instead of failing silently

---

## 🧠 The machine-learning services

| Service | Under the hood | Where it lives |
|---|---|---|
| **Customer Mood** | scikit-learn — TF-IDF vectorizer + logistic regression, trained on the review corpus | `app/services/nlp_service.py` |
| **Product Studio** | TensorFlow / Keras — MobileNetV2 transfer learning over a fashion image dataset | `app/services/cv_service.py` |
| **Boutique Concierge** | Rule-based intents with a TF-IDF + LinearSVC intent classifier as fallback | `app/services/chatbot_service.py` |

Sentiment and chatbot models are **retrained in CI on every push**, so the pipeline proves the models can be built from raw data — not just loaded from a stale file.

### Where the machine learning actually shows up

| Surface | Model | What the user sees |
|---|---|---|
| Style Wall — uploaded photo | MobileNetV2 classifier | "✨ Recognized: bags" chip on the post |
| Style Wall — caption | Sentiment model | "Loved It" / "Mixed Feelings" / "Needs Love" chip |
| Customer Mood page | Sentiment model | Mood + confidence for any pasted text |
| Concierge chat | Intent classifier | Answers to free-form questions |
| `POST /classify-product` | MobileNetV2 classifier | Category + confidence, straight from the API |

The sentiment corpus is deliberately small, so the UI hides a mood label when the model
is unsure (below 0.5 confidence) or when it contradicts the star rating. Adding rows to
`data/reviews.csv` improves the model automatically, since CI retrains on every push.

---

## 🛠️ Tech stack

**Backend** — FastAPI · Uvicorn · Pydantic · JSON storage + append-only event log
**ML** — scikit-learn · TensorFlow/Keras · OpenCV · NumPy · pandas
**Frontend** — React (in-browser Babel, single-file SPA, no build step) · custom CSS design system
**Quality** — pytest · httpx · GitHub Actions (tests + Docker build on every push)
**Infra** — Docker (python:3.11-slim + OpenCV runtime deps) · Netlify (CDN) · Render (API)

---

## 🏗️ Architecture

```
        Browser  (React SPA — single HTML file)
               │  HTTPS, X-API-Key header
               ▼
   ┌── Netlify CDN ──┐          ┌─────────── Render (Docker) ───────────┐
   │  public/        │  REST    │  FastAPI                              │
   │  index.html     │ ───────▶ │   ├─ routers/  (28 endpoints)         │
   └─────────────────┘          │   │   products · cart · favorites ·   │
                                │   │   reviews · recommendations ·     │
   GitHub Actions               │   │   events · funnel · identity ·    │
    ├─ install deps             │   │   nlp · chatbot · vision ·        │
    ├─ train ML models          │   │   stylewall                       │
    ├─ pytest  (17 tests)       │   ├─ services/  nlp · cv · chatbot     │
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
| Styling | `GET /complete-the-look/{product_id}` |
| Events & funnel | `POST /events` · `GET /events/count` · `GET /funnel` |
| Identity | `POST /identity/register` · `POST /identity/login` |
| NLP | `POST /analyze-sentiment` |
| Chatbot | `POST /chatbot` |
| Vision | `POST /classify-product` |
| **Style Wall** | `POST /stylewall/posts` (photo + rating + caption) · `GET /stylewall/posts` · `POST /stylewall/posts/{id}/cheer` · `POST /stylewall/posts/{id}/comments` · `GET /stylewall/summary` |
| Admin | `GET /` · `GET /dashboard/stats` |

### Style Wall in detail

```
POST /stylewall/posts           multipart: photo, rating (1-5), caption, customer, product_id?
                                → 201 with the post: photo_url, cv_tag, sentiment, counts
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

`tests/test_endpoints.py` covers seventeen end-to-end API behaviours: products listing,
API-key rejection (401), sentiment analysis, the chatbot, dashboard stats, the full cart
flow (add → update → checkout intent → bag cleared), the identity flow (register →
duplicate-name handling → wrong secret → successful login), and the Style Wall (auth,
rating validation, non-image rejection, upload → feed, cheer toggling, comments, 404s,
summary), plus guards proving the removed face endpoints now 404.

```bash
pytest tests/ -v      # 17 passed
```

CI (`.github/workflows/deploy.yml`) retrains the models, runs the suite, and builds the
Docker image on every push to `main`.

---

## 📁 Project layout

```
app/
  main.py              FastAPI app — middleware, routers, dashboard
  routers/             12 routers, 28 endpoints
  services/            nlp_service · cv_service · chatbot_service
  models/              sentiment .pkl · MobileNetV2 .h5
  storage.py           small JSON persistence helper
data/
  products.json        the 87-product catalogue
  reviews.json/.csv    customer feedback + training corpus
  favorites.json       wishlists
  carts.json           shopping bags
  events.jsonl         append-only analytics stream
  stylewall.json       Style Wall posts
  stylewall/           uploaded shopper photos
  intents.json         concierge training data
  products/ graphics/  lookbook and UI imagery
frontend/index.html    development copy of the SPA
public/index.html      the deployed storefront
tests/                 pytest suite
Dockerfile             python:3.11-slim, uvicorn, port 8000
```

---

## 🚧 Roadmap

- Persistent uploads (S3/Cloudinary) so the Style Wall survives a redeploy
- Grow `data/reviews.csv` to sharpen the sentiment model
- Move JSON files to Postgres and the event stream to a managed store
- Loyalty + membership card on the shopper profile
- Payments (sandbox) behind the checkout intent

---

Built by **Lavanya Karna** — [github.com/lavanyakarna](https://github.com/lavanyakarna)
