"""
Persistence for reports. MongoDB when available; an in-process store otherwise.

Analysis itself never depends on the database — a missing Mongo instance must
not discard a live LLM report. The frontend can still list reports from the
in-memory store for the lifetime of the API process.
"""
import os
import threading
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

_client = None
_mongo_ok: bool | None = None
_memory: dict[str, dict] = {}
_lock = threading.Lock()


def backend_name() -> str:
    _ensure_mongo()
    return "mongodb" if _mongo_ok else "memory"


def _ensure_mongo() -> bool:
    global _client, _mongo_ok
    if _mongo_ok is not None:
        return _mongo_ok
    if os.environ.get("MONGODB_URI", "").strip().lower() in {"", "memory", "none", "off"}:
        _mongo_ok = False
        return False
    try:
        from pymongo import MongoClient
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri, serverSelectionTimeoutMS=1500)
        _client.admin.command("ping")
        _mongo_ok = True
    except Exception as exc:
        print(f"[storage] Mongo unavailable ({exc}); using in-memory reports.")
        _client = None
        _mongo_ok = False
    return _mongo_ok


def get_db():
    if not _ensure_mongo():
        return None
    return _client["continuity"]


def save_report(script_id: str, report_dict: dict):
    payload = {"script_id": script_id, **report_dict}
    with _lock:
        _memory[script_id] = payload
    db = get_db()
    if db is None:
        return
    try:
        db.reports.update_one(
            {"script_id": script_id},
            {"$set": payload},
            upsert=True,
        )
    except Exception as exc:
        print(f"[storage] Mongo write failed ({exc}); report kept in memory.")


def get_report(script_id: str) -> dict | None:
    db = get_db()
    if db is not None:
        try:
            found = db.reports.find_one({"script_id": script_id}, {"_id": 0})
            if found:
                return found
        except Exception:
            pass
    with _lock:
        stored = _memory.get(script_id)
        return dict(stored) if stored else None


def list_reports() -> list[dict]:
    db = get_db()
    if db is not None:
        try:
            rows = list(db.reports.find({}, {"_id": 0}))
            if rows:
                return rows
        except Exception:
            pass
    with _lock:
        return [dict(v) for v in _memory.values()]
