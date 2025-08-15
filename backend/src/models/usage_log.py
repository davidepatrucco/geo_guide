from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from ..infra.db import usage_logs

_ALLOWED = {
    "app.open", "auth.login", "poi.nearby", "poi.view",
    "narration.request", "narration.generated", "audio.play",
    "contrib.posted", "contrib.moderated", "error"
}

def ensure_indexes():
    usage_logs.create_index([("ts", DESCENDING)], name="ts_desc")
    usage_logs.create_index([("event", ASCENDING), ("ts", DESCENDING)], name="event_ts")
    usage_logs.create_index([("session_id", ASCENDING), ("ts", DESCENDING)], name="session_ts", sparse=True)
    usage_logs.create_index([("user_hash", ASCENDING), ("ts", DESCENDING)], name="user_ts", sparse=True)

def _dt(x):
    return x if isinstance(x, datetime) else datetime.now(timezone.utc)

def _event(ev):
    if not ev or ev not in _ALLOWED:
        return "error", ev
    return ev, None

def log(evt: dict):
    try:
        ev, raw = _event(evt.get("event"))
        evt["event"] = ev
        if raw and raw != ev:
            evt["event_raw"] = raw
        evt["ts"] = _dt(evt.get("ts"))
        usage_logs.insert_one(evt)
    except PyMongoError:
        pass

def list_recent(limit: int = 200):
    return list(usage_logs.find({}).sort("ts", -1).limit(limit))

def by_session(session_id: str, limit: int = 200):
    return list(usage_logs.find({"session_id": session_id}).sort("ts", -1).limit(limit))

def by_user(user_hash: str, limit: int = 200):
    return list(usage_logs.find({"user_hash": user_hash}).sort("ts", -1).limit(limit))