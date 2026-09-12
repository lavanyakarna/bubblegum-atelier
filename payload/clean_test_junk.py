#!/usr/bin/env python3
"""
clean_test_junk.py — removes leftovers that `pytest` left in your real boutique.

Running the test suite used to write into the real data files, which is why the
Style Wall showed posts from "pytest-tagger", "pytest-wall" and friends.

This removes ONLY records belonging to automated tests:
    - Style Wall posts whose author starts with "pytest" (and their photos)
    - Lookbook likes from "pytest..." visitors
    - Concierge chats from "pytest..." visitors
    - Event-log rows with a "pytest..." customer id

Your own posts, likes, chats and analytics are never touched.
Every file it edits gets a .junk-backup copy first.

Usage:
    python clean_test_junk.py --check    # show what would go, change nothing
    python clean_test_junk.py            # clean it
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

STARTS_WITH = "pytest"


def _load(path, default):
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _backup(path: Path, dry: bool):
    if dry or not path.exists():
        return
    shutil.copy2(path, Path(str(path) + ".junk-backup"))


def _is_test(value) -> bool:
    return isinstance(value, str) and value.lower().startswith(STARTS_WITH)


def clean(dry: bool) -> list:
    report = []

    # ---------------------------------------------------------------- Style Wall
    wall_path = DATA / "stylewall.json"
    posts = _load(wall_path, [])
    if isinstance(posts, list):
        keep = [p for p in posts if not _is_test(p.get("customer"))]
        removed = [p for p in posts if _is_test(p.get("customer"))]
        if removed:
            _backup(wall_path, dry)
            if not dry:
                with open(wall_path, "w", encoding="utf-8") as f:
                    json.dump(keep, f, indent=2)
                for p in removed:
                    url = p.get("photo_url") or ""
                    photo = DATA / "stylewall" / os.path.basename(url)
                    if photo.exists():
                        photo.unlink()
            report.append(("Style Wall posts", len(removed), len(keep)))
        else:
            report.append(("Style Wall posts", 0, len(keep)))

    # ---------------------------------------------------------------- Lookbook likes
    likes_path = DATA / "lookbook_likes.json"
    likes = _load(likes_path, {})
    if isinstance(likes, dict):
        cleaned, dropped = {}, 0
        for look_id, people in likes.items():
            people = people or []
            kept_people = [c for c in people if not _is_test(c)]
            dropped += len(people) - len(kept_people)
            if kept_people:
                cleaned[look_id] = kept_people
        if dropped:
            _backup(likes_path, dry)
            if not dry:
                with open(likes_path, "w", encoding="utf-8") as f:
                    json.dump(cleaned, f, indent=2)
        report.append(("Lookbook likes", dropped, 0))

    # ---------------------------------------------------------------- chats
    chats_path = DATA / "chats.json"
    chats = _load(chats_path, [])
    if isinstance(chats, list):
        keep = [c for c in chats if not _is_test(c.get("customer"))]
        removed = len(chats) - len(keep)
        if removed:
            _backup(chats_path, dry)
            if not dry:
                with open(chats_path, "w", encoding="utf-8") as f:
                    json.dump(keep, f, indent=2)
        report.append(("Concierge chats", removed, len(keep)))

    # ---------------------------------------------------------------- event log
    events_path = DATA / "events.jsonl"
    if events_path.exists():
        lines = events_path.read_text(encoding="utf-8").splitlines()
        keep_lines, dropped = [], 0
        for line in lines:
            text = line.strip()
            if not text:
                continue
            try:
                entry = json.loads(text)
            except json.JSONDecodeError:
                keep_lines.append(text)
                continue
            if isinstance(entry, dict) and _is_test(entry.get("customer_id")):
                dropped += 1
            else:
                keep_lines.append(text)
        if dropped:
            _backup(events_path, dry)
            if not dry:
                events_path.write_text("\n".join(keep_lines) + "\n", encoding="utf-8")
        report.append(("Event-log rows", dropped, len(keep_lines)))

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove automated-test leftovers from your boutique data.")
    ap.add_argument("root", nargs="?", default=".", help="project root (default: current directory)")
    ap.add_argument("--check", action="store_true", help="show what would be removed, change nothing")
    args = ap.parse_args()

    global ROOT, DATA
    ROOT = Path(args.root).resolve()
    DATA = ROOT / "data"

    if not DATA.is_dir():
        print(f"No data/ folder in {ROOT}")
        return 2

    print(f"Project root : {ROOT}")
    print(f"Mode         : {'DRY RUN' if args.check else 'CLEAN'}\n")

    report = clean(args.check)
    total = 0
    for label, removed, kept in report:
        total += removed
        line = f"  {label:<20} removed {removed:>3}"
        if kept:
            line += f"   kept {kept}"
        print(line)

    print()
    if total == 0:
        print("Nothing to clean - your data is already tidy.")
    elif args.check:
        print(f"Would remove {total} test record(s). Re-run without --check to clean them.")
    else:
        print(f"Removed {total} test record(s). Backups saved as *.junk-backup")
        print("Refresh your browser - the wall should show only real posts now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
