# 🌸 Style Wall — install guide

This update does three things to Bubblegum Atelier:

1. **Removes Customer Memory entirely** — face recognition, the Add Guest / Recognize
   Guest screens, the face model files, the visits log. Gone from the code and the UI.
2. **Adds the Style Wall** — shoppers upload a photo of what they bought, rate it,
   cheer each other's posts and leave comments.
3. **Makes the ML visible** — every uploaded photo is read by the vision model
   ("Recognized: shoes") and every caption is read by the sentiment model
   ("Loved It"). Two of your four brains now show up where people can see them.

---

## What's in here

```
apply_stylewall.py          the installer
stylewall_payload/          the files it copies in
  app/main.py                 registers the Style Wall router
  app/routers/stylewall.py    the new API (5 endpoints)
  app/routers/vision.py       face endpoints removed, classifier kept
  app/routers/events.py       accepts wall_post / wall_cheer / wall_comment
  app/services/cv_service.py  face service removed
  tests/test_endpoints.py     17 tests (9 new, covering the wall + the removals)
INSTALL-STYLEWALL.md        this file
```

No new dependencies — `opencv`, `python-multipart` and `fastapi` are already in your
`requirements.txt`.

---

## Install (3 commands)

Put `apply_stylewall.py` and the `stylewall_payload/` folder **in your project root**
(the folder containing `app/` and `public/`), then:

```powershell
cd "C:\Users\lavan\OneDrive\Desktop\Bubblegum atelier"

python apply_stylewall.py --check     # 1. dry run - shows every edit, changes nothing
python apply_stylewall.py             # 2. the real install
pytest tests/ -v                      # 3. expect: 17 passed
```

The installer:
- copies the backend files in, saving a `.pre-stylewall.bak` copy of anything it replaces
- patches **both** `public/index.html` and `frontend/index.html`
- deletes the Customer Memory files (`--keep-memory` keeps them instead)

Every edit is anchored on exact text from your current files. If something doesn't
match, it prints `FAILED` for that step rather than guessing — send me the output and
we'll sort it.

---

## Verify it on your machine

```powershell
# backend
uvicorn app.main:app --reload --port 8000
# open http://127.0.0.1:8000/docs -> you should see a "stylewall" group with 5 endpoints

# frontend
# open public/index.html with Live Server, sign in, look for "Style Wall" in the sidebar
```

Things worth trying, in order:

| Try this | What should happen |
|---|---|
| Style Wall → pick a photo, 5 stars, type a caption, Share | Post appears at the top of the wall instantly |
| Look at the new card | Photo, stars, your name, "just now" |
| (with TensorFlow installed) upload a garment photo | Chip appears: ✨ Recognized: shoes |
| Hover the heart, click it | Count goes 0 → 1, heart fills pink, the event is logged |
| Click it again | Cheer is taken back (it's a toggle, one per person) |
| Click the speech bubble | Comments panel opens, existing comments show |
| Type a comment and press Enter | Comment appears immediately, with your name |
| Sidebar | No Customer Memory anywhere |

---

## Ship it

```powershell
git add .
git rm --cached app/models/face_db.pkl app/models/face_lbph.yml app/models/haarcascade_frontalface_default.xml data/customer_visits.csv
git commit -m "feat: Style Wall (photo upload, ratings, cheers, comments); remove Customer Memory"
git push
```

CI runs the 17 tests and rebuilds the Docker image. Render redeploys the API.
Netlify redeploys the storefront.

> **One free-tier caveat, stated plainly:** Render wipes the container filesystem on
> every redeploy, so shopper uploads live in `data/stylewall/` and survive only until
> the next deploy. The wall will look empty again after a push. That's a hosting
> limitation, not a bug — the honest fix is a paid instance with a persistent disk,
> or moving uploads to S3/Cloudinary later. Worth one line in the README.

---

## A note on the mood model

While testing I fed the wall a glowing 5-star review —

> "These heels are gorgeous, wore them to a wedding and got so many compliments"

— and the sentiment model called it **negative at 37% confidence**. That's not a bug in
the wall: `data/reviews.csv` is a small corpus, so the model is close to guessing on
novel sentences.

So the UI now refuses to show a mood chip that would look silly:

- confidence below 0.5 → no chip
- a 4–5★ post read as "negative" (or a 1–2★ post read as "positive") → no chip

The real fix is more training data — every row added to `data/reviews.csv` gets picked
up automatically, because CI retrains the model on every push.

---

## Rolling back

```powershell
# the patched files:
Get-ChildItem -Recurse -Filter *.pre-stylewall.bak | ForEach-Object {
  Copy-Item $_.FullName ($_.FullName -replace '\.pre-stylewall\.bak$','') -Force
}
# the deleted memory files:
git checkout HEAD -- app/models data/customer_visits.csv
```
