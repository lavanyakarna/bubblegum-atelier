"""
Chatbot Service — the Boutique Concierge.

How it answers, in order:

  1. PRODUCT LOOKUP   - "how much are the sugar rush heels?" / "show me bags"
                        Reads the real catalogue: prices, sizes, stock.
  2. RULES            - whole-word matching against known phrasings.
                        (The old version used substring matching, so the greeting
                         pattern "hi" matched inside "shipping" and "which".)
  3. ML CLASSIFIER    - TF-IDF + logistic regression over data/intents.json.
                        Answers are dropped when confidence is low, so the bot
                        says something useful instead of something wrong.
  4. HONEST FALLBACK  - tells the shopper what it *can* help with.

Run this file directly once to train and save the model:
    python -m app.services.chatbot_service
It reads data/intents.json and writes:
    app/models/chatbot_model.pkl   (vectorizer + classifier + responses + patterns)
"""

import json
import os
import random
import re

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
MODEL_DIR = os.path.join(BASE_DIR, "models")
ROOT_DIR = os.path.dirname(BASE_DIR)
INTENTS_PATH = os.path.join(ROOT_DIR, "data", "intents.json")
PRODUCTS_PATH = os.path.join(ROOT_DIR, "data", "products.json")
MODEL_PATH = os.path.join(MODEL_DIR, "chatbot_model.pkl")

# how sure the ML model must be before its answer is trusted
MIN_CONFIDENCE = 0.34

WORD_RE = re.compile(r"[a-z0-9']+")

CATEGORY_WORDS = {
    "shoes": ["shoe", "shoes", "heels", "sneakers", "flats", "footwear", "sandals", "boots"],
    "bags": ["bag", "bags", "handbag", "handbags", "crossbody", "tote", "clutch", "purse"],
    "dresses": ["dress", "dresses", "frock", "gown"],
    "tops": ["top", "tops", "shirt", "blouse", "tee", "sweater", "cardigan", "knit"],
    "bottoms": ["bottom", "bottoms", "jeans", "skirt", "trousers", "pants", "denim", "shorts"],
    "accessories": ["accessory", "accessories", "jewellery", "jewelry", "necklace", "earrings", "scarf", "belt", "watch"],
    "makeup": ["makeup", "lipstick", "gloss", "foundation", "blush", "mascara", "eyeshadow", "liner", "palette"],
}

# words that carry no meaning on their own - never use these to match intents
SKIP_WORDS = {
    "the", "a", "an", "is", "are", "am", "was", "were", "be", "been", "do", "does", "did",
    "you", "your", "have", "has", "had", "my", "me", "i", "we", "us", "our", "of", "for",
    "in", "on", "at", "to", "from", "how", "much", "many", "what", "which", "who", "when",
    "where", "why", "show", "any", "some", "and", "or", "with", "this", "that", "these",
    "those", "it", "its", "can", "could", "would", "should", "get", "got", "buy", "please",
    "there", "here", "about", "tell", "give", "want", "need", "looking", "look", "help",
    "know", "like", "just", "also", "very", "so", "if", "then", "than", "as", "by", "not",
}

# words that mean "I'm asking about a product" rather than about a policy
CATALOGUE_SIGNALS = {
    "show", "browse", "see", "sell", "sells", "sold", "available", "availability",
    "price", "prices", "cost", "costs", "much", "stock", "size", "sizes", "fit", "fits",
    "colour", "color", "colours", "colors", "options", "collection", "range", "buy",
    "have", "has", "any", "looking", "want", "need", "browsing", "shopping",
}

# if one of these appears, the shopper is asking about a policy or an order, not a product
POLICY_WORDS = {
    "return", "returns", "returning", "refund", "refunds", "exchange", "exchanges",
    "cancel", "cancelled", "ship", "ships", "shipping", "deliver", "delivery", "delivered",
    "payment", "payments", "pay", "track", "tracking", "order", "orders", "warranty",
    "guarantee", "wash", "washing", "care", "clean", "hours", "open", "close", "closed",
    "member", "membership", "loyalty", "points", "feedback", "review", "reviews",
    "support", "contact", "human", "complaint", "damaged", "defective", "wrong", "broken",
    "address", "gift", "wrap", "wrap", "coupon", "code", "discount", "offer", "offers",
    "sale", "promo", "warranty",
}


def load_intents():
    with open(INTENTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["intents"] if isinstance(data, dict) else data


def _load_products():
    try:
        with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("products", [])
    except (OSError, json.JSONDecodeError):
        return []


def train_chatbot_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    intents = load_intents()

    patterns, tags, responses = [], [], {}
    for intent in intents:
        responses[intent["tag"]] = intent["responses"]
        for p in intent["patterns"]:
            patterns.append(p.lower())
            tags.append(intent["tag"])

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    X = vectorizer.fit_transform(patterns)

    # logistic regression gives probabilities, so we can decline to answer when unsure
    clf = LogisticRegression(max_iter=1200, C=6.0)
    clf.fit(X, tags)

    accuracy = clf.score(X, tags)
    joblib.dump({
        "vectorizer": vectorizer,
        "classifier": clf,
        "responses": responses,
        "raw_patterns": list(zip(patterns, tags)),
    }, MODEL_PATH)
    print(f"Trained on {len(patterns)} phrases across {len(intents)} intents "
          f"(fit score {accuracy:.2f}) -> {MODEL_PATH}")


class ChatbotService:
    def __init__(self):
        bundle = joblib.load(MODEL_PATH)
        self.vectorizer = bundle["vectorizer"]
        self.classifier = bundle["classifier"]
        self.responses = bundle["responses"]
        self.raw_patterns = bundle.get("raw_patterns", [])
        self.products = _load_products()
        self._word_patterns = [
            (self._content_words(self._tokens(p)), t) for p, t in self.raw_patterns
        ]

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _tokens(text: str):
        return WORD_RE.findall(text.lower())

    def _find_products(self, message: str):
        """Which catalogue pieces is the shopper asking about?"""
        msg = message.lower()
        tokens = set(self._tokens(msg))
        hits = []

        for p in self.products:
            name = p.get("name", "")
            name_lower = name.lower()
            if name_lower and name_lower in msg:                    # full name quoted
                hits.append((3.0, p))
                continue
            name_tokens = [w for w in self._tokens(name) if len(w) > 2 and w not in SKIP_WORDS]
            if not name_tokens:
                continue
            overlap = len(tokens & set(name_tokens))
            if overlap >= 2:
                hits.append((overlap / len(name_tokens), p))

        hits.sort(key=lambda x: x[0], reverse=True)
        seen, out = set(), []
        for score, p in hits:
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            out.append(p)
        return out[:3]

    def _find_category(self, message: str):
        """'show me bags' -> ('bags', [...products])"""
        tokens = set(self._tokens(message))
        for category, words in CATEGORY_WORDS.items():
            if tokens & set(words):
                items = [p for p in self.products if p.get("category") == category]
                return category, items
        return None, []

    @staticmethod
    def _price(p):
        return f"{p.get('currency', 'INR')} {p.get('price')}"

    def _product_answer(self, message: str):
        """Answer about specific pieces, or a whole category, using real catalogue data."""
        tokens = set(self._tokens(message))

        found = self._find_products(message)
        if found:
            parts = []
            for p in found[:2]:
                sizes = ", ".join(p.get("sizes", []) or [])
                stock = "in stock" if p.get("in_stock") else "currently sold out"
                line = f"{p['name']} ({p.get('category', 'piece')}) is {self._price(p)} and {stock}"
                if sizes:
                    line += f". Sizes: {sizes}"
                parts.append(line)
            return {
                "intent": "product_lookup",
                "reply": " | ".join(parts) + ". You can open it in the Shop tab.",
                "method": "catalogue",
            }

        category, items = self._find_category(message)
        if category and items:
            wants_size = bool(tokens & {"size", "sizes", "fit"})
            sample = items[:3]
            listed = "; ".join(f"{p['name']} - {self._price(p)}" for p in sample)
            reply = f"We have {len(items)} pieces in {category}. For example: {listed}."
            if wants_size:
                sizes = sorted({s for p in items for s in (p.get("sizes") or []) if s.lower() != "one size"})
                if sizes:
                    reply += f" Available sizes across them: {', '.join(sizes)}."
            return {"intent": "category_lookup", "reply": reply, "method": "catalogue"}

        if tokens & {"price", "prices", "cost", "how", "much"} and tokens & {"bag", "dress", "shoe", "top"}:
            # a category word we didn't catch - stay useful rather than guessing
            return {
                "intent": "category_help",
                "reply": "Tell me the piece or the category - for example 'show me bags' or 'how much are the sugar rush heels'.",
                "method": "catalogue",
            }
        return None

    @staticmethod
    def _content_words(tokens):
        """Meaningful words only - 'do you have' must never decide an answer."""
        return {w for w in tokens if w not in SKIP_WORDS and len(w) > 1}

    def _rule_based_match(self, message: str):
        """
        Match on meaningful words, not filler.

        Two shoppers asking 'show me bags' and 'do you have bags' share only the word
        'bags' - so 'bags' has to be what decides the answer.
        """
        tokens = self._content_words(self._tokens(message))
        if not tokens:
            return None

        best, best_score = None, 0.0
        for pattern_content, tag in self._word_patterns:
            if not pattern_content:            # pattern was pure filler - never match on it
                continue
            overlap = len(tokens & pattern_content)
            if overlap == 0:
                continue
            coverage = overlap / len(pattern_content)

            # Trust a match only when it's substantial: either two or more meaningful
            # words line up, or the pattern is almost entirely present.
            # Without this, "show me bags" matched "warranty on bags" on the word "bags".
            if overlap < 2 and coverage < 0.75:
                continue

            score = overlap * coverage
            if score > best_score:
                best, best_score = tag, score
        return best

    def _ml_match(self, message: str):
        vec = self.vectorizer.transform([message.lower()])
        try:
            proba = self.classifier.predict_proba(vec)[0]
            idx = int(proba.argmax())
            confidence = float(proba[idx])
            if confidence < MIN_CONFIDENCE:
                return None, confidence
            return self.classifier.classes_[idx], confidence
        except (AttributeError, ValueError):
            # an older model without predict_proba - use it but trust it less
            return self.classifier.predict(vec)[0], 1.0

    # ------------------------------------------------------------------ main

    def get_reply(self, message: str) -> dict:
        message = (message or "").strip()
        if not message:
            return {
                "intent": "empty",
                "reply": "Ask me anything - sizes, shipping, returns, or say 'show me bags'.",
                "method": "fallback",
            }

        words = set(self._tokens(message))

        # 1. a specific piece, named outright - always answer from the catalogue
        catalogue = self._product_answer(message)
        if catalogue and catalogue["intent"] == "product_lookup":
            return catalogue

        # 2. a policy or order question
        tag = self._rule_based_match(message)
        if tag:
            return {"intent": tag, "reply": random.choice(self.responses.get(tag, ["Happy to help!"])), "method": "rule"}

        # 3. browsing a category ("show me bags", "what sizes do the heels come in")
        #    - unless they're actually asking about returns, shipping and so on
        asking_about_policy = bool(words & POLICY_WORDS)
        wants_catalogue = bool(words & CATALOGUE_SIGNALS)
        if catalogue and catalogue["intent"] == "category_lookup" and wants_catalogue and not asking_about_policy:
            return catalogue

        # 4. the trained model, if it's confident
        tag, confidence = self._ml_match(message)
        if tag:
            return {"intent": tag, "reply": random.choice(self.responses.get(tag, ["Happy to help!"])), "method": "ml"}

        # 5. a category mention was there after all
        if catalogue and not asking_about_policy:
            return catalogue

        return {
            "intent": "unknown",
            "reply": ("I'm not certain about that one. I'm good with: product prices and sizes "
                      "('how much are the sugar rush heels'), categories ('show me bags'), store hours, "
                      "shipping, delivery times, returns, exchanges, payment methods, and order help."),
            "method": "fallback",
        }


if __name__ == "__main__":
    train_chatbot_model()
