# Bubblegum Atelier — AI Smart Retail Platform

An AI-powered backend platform for retail businesses, combining computer vision, NLP, and a chatbot behind a single documented REST API. Built with FastAPI, OpenCV, and TensorFlow/Keras.

## About

This project brings together four AI capabilities into one retail-focused backend: facial recognition for returning-customer tracking (Customer Memory), image classification for sorting product photos into categories (Product Studio), sentiment analysis for reading customer reviews (Customer Mood), and a rule-based FAQ chatbot (Boutique Concierge). Everything is exposed through a single documented REST API, with a lightweight dashboard on top summarizing visits and customer activity.

## Features

- **Customer Memory** — Face recognition (OpenCV LBPH) to register and recognize returning customers, logging visits automatically.
- **Product Studio** — Image classification (MobileNetV2 transfer learning) that sorts product photos into categories: shoes, bags, clothing, accessories, makeup.
- **Customer Mood** — Sentiment analysis on customer reviews/feedback (positive / negative / neutral).
- **Boutique Concierge** — A rule-based FAQ chatbot answering questions about hours, returns, and shipping.
- **Dashboard** — Aggregate stats endpoint summarizing visits and unique customers.

## Tech Stack

- **Backend:** FastAPI (Python)
- **Computer Vision:** OpenCV (Haar cascades, LBPH face recognition)
- **Deep Learning:** TensorFlow / Keras (MobileNetV2 transfer learning)
- **Frontend:** HTML, React (via in-browser Babel), custom pastel "boutique" UI
- **Auth:** API key–based request authentication

## API Overview

All endpoints require the header X-API-Key.

| Endpoint | Method | Description |
|---|---|---|
| /chatbot | POST | Send a message, get an FAQ-based reply |
| /analyze-sentiment | POST | Analyze sentiment of review/feedback text |
| /classify-product | POST | Upload a product photo, get predicted category |
| /register-face | POST | Register a customer's face (3–5 photos) |
| /recognize-face | POST | Recognize a customer from a photo |
| /dashboard/stats | GET | Aggregate visit/customer stats |

Full interactive API docs are available at /docs (Swagger UI) once the server is running.

## Getting Started

### Backend

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

Backend runs at http://127.0.0.1:8000

### Frontend

Open frontend/index.html directly in your browser. Make sure the backend is running first.

## Project Structure

smart-retail-ai/
- app/
  - main.py — FastAPI entrypoint, CORS, auth
  - routers/ — API route handlers (vision.py, nlp.py, chatbot.py)
  - services/ — Core logic (cv_service.py, nlp_service.py, chatbot_service.py)
  - models/ — Trained model files (.h5, .yml, .pkl)
- data/ — Training data, logs
- notebooks/ — Model training notebooks
- frontend/
  - index.html — UI
- requirements.txt

## Ethical Considerations

This project uses facial recognition, which raises real privacy and consent concerns. In a production deployment:
- Customers should explicitly opt in before their face is registered.
- Face data should be stored securely and deleted on request.
- Recognition accuracy can vary across demographics; results should not be used for any decision with legal or safety consequences without human review.
- This project is an academic/portfolio prototype and is not intended for production use without further privacy and fairness auditing.

## Quick start

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Train the sentiment model (uses data/reviews.csv)
python -m app.services.nlp_service

# Train the chatbot intent model (uses data/intents.json)
python -m app.services.chatbot_service

# (Optional, needs a real image dataset) train the product classifier:
# open notebooks/01_image_classifier_training.ipynb in Jupyter and run all cells

# Run the API
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive Swagger docs.

All endpoints require an `X-API-Key` header. Default dev key is `dev-key-123`
(set via `RETAIL_API_KEY` env var in production).

## Endpoints

| Endpoint | Method | Body | Notes |
|---|---|---|---|
| `/register-face` | POST | form: `name`, `files[]` | upload 3-5 photos to register a customer |
| `/recognize-face` | POST | form: `file` | upload one photo, returns match or unknown |
| `/classify-product` | POST | form: `file` | returns category (needs trained model) |
| `/analyze-sentiment` | POST | json: `{"text": "..."}` | positive/negative/neutral |
| `/chatbot` | POST | json: `{"message": "..."}` | FAQ reply |
| `/dashboard/stats` | GET | — | visit counts |

## Tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker build -t smart-retail-ai .
docker run -p 8000:8000 -e RETAIL_API_KEY=your-key smart-retail-ai
```

