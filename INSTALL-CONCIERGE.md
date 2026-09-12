# 💬 Concierge upgrade + cleanup guide

Two things you asked about, both fixed and tested.

---

## 1. The odd-looking wall — my fault, now cleaned

Those posts from **pytest-tagger**, **pytest-cheerer** and **pytest-wall** were written
by the automated tests. Running `pytest` was writing into your real boutique data, so
every test run added fake posts and fake likes.

Two fixes:

**a) The mess is cleaned.** The update removes only records belonging to automated
tests, and leaves every real post, like, chat and analytics row alone. Your data is
backed up first (`.junk-backup` files), so nothing is lost.

**b) It can't happen again.** A new `tests/conftest.py` takes a snapshot of your data
before the test suite runs and puts it back afterwards — including deleting any files
the tests created. I verified this by hashing your data files before and after a full
run: **identical**.

---

## 2. The concierge — rebuilt

### The actual bug

The old matcher did this:

```python
if pattern in message or message in pattern:
```

Substring matching. So the greeting pattern **"hi"** matched inside *"w**hi**ch"*,
*"t**hi**s"* and *"s**hi**pping"*. Ask about shipping charges and the bot might say
"Hello! Welcome to Bubblegum Atelier."

### What it does now

| Before | After |
|---|---|
| 22 intents, 67 example phrases | **30 intents, 214 phrases** |
| Substring matching | Whole meaningful words only — "do you have" can never decide an answer |
| Only policy answers | **Real catalogue answers** from your products.json |
| "Sorry, I didn't understand" | Honest fallback that says what it *can* do |
| LinearSVC (no confidence) | Logistic regression — declines to answer when unsure |

### It can now answer questions about your actual products

```
you: how much are the sugar rush platform heels
bot: Sugar Rush Platform Heels (shoes) is INR 2499 and in stock. Sizes: 5, 6, 7, 8.
     You can open it in the Shop tab.                                    (catalogue)

you: show me bags
bot: We have 13 pieces in bags. For example: Petal Pop Mini Crossbody - INR 1799;
     Confetti Tote - INR 2199; ...                                       (catalogue)

you: are the bow sneakers in stock
bot: Bubblegum Bow Sneakers (shoes) is INR 1899 and in stock. Sizes: 4, 5, 6, 7, 8.

you: how much is shipping
bot: Shipping is free on orders over INR 1499 - below that it's a flat INR 79.  (rule)

you: can i return this bag          <- policy question, not a bag question
bot: Returns are free within 14 days for unworn pieces.                         (ml)

you: what is the meaning of life
bot: I'm not certain about that one. I'm good with: product prices and sizes
     ('how much are the sugar rush heels'), categories ('show me bags'), store
     hours, shipping...                                                        (fallback)
```

That last one matters: **it admits when it doesn't know** instead of inventing an
answer. That's the same principle as the mood label on the Style Wall.

---

## Install (3 commands)

Put `apply_chat_update.py`, `clean_test_junk.py` and the `payload/` folder **in your
project root**, then:

```powershell
cd "C:\Users\lavan\OneDrive\Desktop\Bubblegum atelier"

python apply_chat_update.py --check     # 1. shows every change, modifies nothing
python apply_chat_update.py             # 2. installs, retrains, cleans the junk
pytest tests/ -v                        # 3. expect: 34 passed
```

The installer will:
- replace the concierge files (`.pre-chatupdate.bak` backups kept)
- retrain the chatbot model on the 214 phrases
- clean the test leftovers (`.junk-backup` backups kept)

Add `--no-clean` if you'd rather clean separately, or `--no-train` to skip retraining.

---

## Verify it

```powershell
uvicorn app.main:app --reload --port 8000
```

Open the storefront, click **Concierge**, and try:

1. `how much is shipping` → should talk about delivery, **not** say hello
2. `show me bags` → lists your real bags with prices
3. `how much are the sugar rush platform heels` → `INR 2499`, sizes 5–8
4. `what is the meaning of life` → honest "I'm not certain" with suggestions

Then check the **Style Wall** — the pytest posts should be gone, your own skirt post
still there.

---

## Ship it

```powershell
git add .
git commit -m "feat: smarter concierge (catalogue answers, 214 phrases, whole-word matching); test data isolation"
git push
```

CI retrains the models from `data/intents.json` and runs all 34 tests on every push, so
the new concierge knowledge ships with the code.

---

## Still open

**Retraining is part of deploy, not startup.** The live server uses the trained
`chatbot_model.pkl`. That file is rebuilt in CI on every push, so this update is live
as soon as it deploys. If you ever edit `intents.json` by hand, run
`python -m app.services.chatbot_service` before pushing.

**The free-tier nap** is still there — a keep-alive ping (UptimeRobot, every 5 minutes)
is the free fix, described in the earlier update guide.
