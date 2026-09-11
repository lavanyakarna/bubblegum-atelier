import json
import os
import tempfile
import threading
from datetime import datetime, timezone

_lock = threading.Lock()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
DATA_DIR = os.path.join(BASE_DIR, "data")


def _path(name):
    return os.path.join(DATA_DIR, name)


def read_json(name, default):
    """Read a JSON file from data/. Returns `default` if missing/broken."""
    p = _path(name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(name, data):
    """Safely write JSON (temp file + replace, so files never get corrupted)."""
    p = _path(name)
    with _lock:
        fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, p)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise


def append_event(event: dict):
    """Append one event line to data/events.jsonl"""
    event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    with _lock:
        with open(_path("events.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events():
    """Read all events as a list of dicts."""
    events = []
    p = _path("events.jsonl")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return events