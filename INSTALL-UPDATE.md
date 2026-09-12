# 🌸 Bubblegum Atelier — update guide

One update, four things fixed. Everything below is tested before it reaches you:
**27 backend tests** and **32 browser checks** passed, plus a live run against your
real 2,037-event log.

---

## What this update does

### 1. ⚡ Your site loads much faster
Your welcome image was 1.33 MB and displayed at 320 pixels wide. Four pictures were
20× bigger than anyone could see.

| | Before | After |
|---|---|---|
| 4 decorative pictures | 4.41 MB | **0.14 MB** (97% smaller) |
| Product photos | all 87 at once | **only the ones on screen** |
| First visit total | ~9.5 MB | **~0.5 MB** |

Same pictures, same pink look — I compared them pixel by pixel and the difference is
invisible to the eye.

### 2. ✨ AI Insights are real now
They used to be four pieces of sample text, including one mentioning the face
recognition feature you removed. They're now computed from your actual event log on
every page load. With your real data, they read:

- *Shoes draw the most attention* — 328 views on shoes, about 17% of everything browsed
- *'Dollhouse Knit Cardigan' is the most-viewed piece* — 49 views, listed at INR 1699
- *1.1% of product views become bag adds* — 22 bag adds from 1,979 views
- *6 items saved to wishlists*
- *33% of reviews are loved*
- *Style Wall photos mostly read as bags* — 9 looks, averaging 4.7 stars

### 3. 🖱️ The four stat cards are clickable
Click any card and a panel opens with the real numbers behind it:

| Card | What opens |
|---|---|
| **Total Visits** | last 24h count, a 7-day bar chart, views by category, most-viewed pieces with photos |
| **Unique Customers** | every visitor (guest ids masked), their action count, who came back |
| **Products Tagged** | every photo the vision model has read, with confidence percentages |
| **Concierge Chats** | real questions shoppers asked and what the bot answered |

The numbers are now **all-time totals** instead of "this session" counters that reset.

### 4. ❤️ The Lookbook has a like button
Every look gets a heart with a live count. One like per visitor, tap again to take it
back. The old "Add whole look" button is still there, right beside it.

---

## Install (3 commands)

Put `apply_update.py`, `update_payload/` and `graphics_optimized/` **in your project
root** (the folder with `app/` and `public/` in it), then:

```powershell
cd "C:\Users\lavan\OneDrive\Desktop\Bubblegum atelier"

python apply_update.py --check     # 1. dry run: shows every edit, changes nothing
python apply_update.py             # 2. install (backs everything up first)
pytest tests/ -v                   # 3. expect: 27 passed
```

Every file it replaces gets a `.pre-update.bak` copy, and your data files are never
overwritten — new ones are only created if missing.

---

## Verify it yourself

```powershell
uvicorn app.main:app --reload --port 8000
```

Then open `public/index.html` with Live Server and check:

| Do this | You should see |
|---|---|
| Open the storefront | Pictures load noticeably faster |
| Sign in as **owner** → Overview | AI Insights show *your* real numbers |
| Click **Total Visits** | Panel with the 7-day chart and most-viewed pieces |
| Click **Unique Customers** | The visitor list, ids masked |
| Click **Products Tagged** | Vision results and confidence |
| Click **Concierge Chats** | Real questions and answers |
| Go to **Lookbook**, tap a heart | Count goes up; tap again and it goes down |

**Note on "Products Tagged":** it starts empty because tag events weren't recorded
before this update. It fills up as people share photos on the Style Wall — every
upload is now logged. Your 9 existing wall posts keep their tags; new ones also count.

---

## Ship it

```powershell
git add .
git commit -m "perf: 97% lighter images + lazy loading; real dashboard insights; clickable stat cards; lookbook likes"
git push
```

Netlify rebuilds the storefront (~30 s), Render rebuilds the API (~2–3 min).

---

## Rolling back

```powershell
Get-ChildItem -Recurse -Filter *.pre-update.bak | ForEach-Object {
  Copy-Item $_.FullName ($_.FullName -replace '\.pre-update\.bak$','') -Force
}
```

---

## Still open (not in this update)

**The server still naps.** Render's free tier sleeps after ~15 minutes idle, so the
first visitor waits 30–60 seconds. This update can't fix that — only hosting can.

Free fix, 5 minutes: create a free account at [uptimerobot.com](https://uptimerobot.com),
add an **HTTP(s)** monitor for `https://bubblegum-atelier.onrender.com/` checking every
**5 minutes**. The server stays awake and nobody ever meets the cold start again.

Paid fix: Render's always-on instance (~$7/mo).

**Uploads still vanish on redeploy.** Render wipes the filesystem on each push, so
Style Wall photos and their likes reset. Fine for a demo; the fix is S3/Cloudinary
storage when it matters.
