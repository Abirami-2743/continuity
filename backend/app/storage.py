"""
MongoDB persistence layer. Story-state and reports are written here so the
system has real persistent memory across requests/scripts, not just
in-process state that vanishes between calls.
"""
import os
from pymongo import MongoClient

_client: MongoClient | None = None


def get_db():
    global _client
    if _client is None:
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri)
    return _client["continuity"]


def save_report(script_id: str, report_dict: dict):
    db = get_db()
    db.reports.update_one(
        {"script_id": script_id},
        {"$set": {"script_id": script_id, **report_dict}},
        upsert=True,
    )


def get_report(script_id: str) -> dict | None:
    db = get_db()
    return db.reports.find_one({"script_id": script_id}, {"_id": 0})


def list_reports() -> list[dict]:
    db = get_db()
    return list(db.reports.find({}, {"_id": 0}))
