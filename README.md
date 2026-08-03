# Smart Retail & Customer Intelligence Platform

Face recognition + product image classification + review sentiment + FAQ chatbot,
all served through one FastAPI app.

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

## What's real vs. what you still need to add

- **Sentiment + chatbot**: fully trained on the sample data included here (`data/reviews.csv`,
  `data/intents.json`). Swap in a bigger dataset (Kaggle "Women's E-Commerce Clothing Reviews")
  and retrain the same way for higher accuracy.
- **Face recognition**: the LBPH pipeline is fully working — register faces via the API or
  `notebooks/02_face_recognition_setup.ipynb`.
- **Product classifier**: code is real (MobileNetV2 transfer learning), but needs an actual
  image dataset to train on — see `notebooks/01_image_classifier_training.ipynb`. Until you
  train it, `/classify-product` returns `{"status": "not_trained"}` instead of crashing.
