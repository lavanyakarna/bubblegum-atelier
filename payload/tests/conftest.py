"""
Test isolation.

The test suite exercises the real API, which writes to the real data files. Without
this file, running `pytest` leaves test posts on the Style Wall, test likes on the
Lookbook and test rows in the event log - visible to actual shoppers.

This fixture snapshots data/ before the suite runs and puts it back afterwards,
including deleting any files the tests created.
"""

import json
import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# files the tests may touch
TRACKED = [
    "stylewall.json", "lookbook_likes.json", "chats.json", "events.jsonl",
    "reviews.json", "favorites.json", "carts.json", "customers.json",
    "order_intents.json",
]


def _snapshot():
    state = {"files": {}, "photos": set()}
    for name in TRACKED:
        path = DATA / name
        state["files"][name] = path.read_text(encoding="utf-8") if path.exists() else None

    photo_dir = DATA / "stylewall"
    if photo_dir.is_dir():
        state["photos"] = {p.name for p in photo_dir.glob("*.jpg")}
    return state


def _restore(state):
    for name, content in state["files"].items():
        path = DATA / name
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.write_text(content, encoding="utf-8")

    photo_dir = DATA / "stylewall"
    if photo_dir.is_dir():
        for photo in photo_dir.glob("*.jpg"):
            if photo.name not in state["photos"]:
                photo.unlink()


@pytest.fixture(scope="session", autouse=True)
def clean_data_after_tests():
    """Run the whole suite, then leave data/ exactly as we found it."""
    if not DATA.is_dir():
        yield
        return

    before = _snapshot()
    yield
    _restore(before)
    print("\n[conftest] test data cleaned up - your real wall, likes and logs are untouched")
