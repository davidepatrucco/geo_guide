from pymongo import ASCENDING, DESCENDING
from ..infra.db import usage_logs

def ensure_indexes():
    usage_logs.create_index([("ts", DESCENDING)], name="ts_desc")
    usage_logs.create_index([("event", ASCENDING), ("ts", DESCENDING)], name="event_ts")
    usage_logs.create_index([("session_id", ASCENDING), ("ts", DESCENDING)], name="session_ts", sparse=True)
    usage_logs.create_index([("user_hash", ASCENDING), ("ts", DESCENDING)], name="user_ts", sparse=True)

def log(evt: dict): usage_logs.insert_one(evt)
def list_recent(limit=200): return list(usage_logs.find({}).sort("ts",-1).limit(limit))
def by_session(session_id, limit=200): return list(usage_logs.find({"session_id":session_id}).sort("ts",-1).limit(limit))
def by_user(user_hash, limit=200): return list(usage_logs.find({"user_hash":user_hash}).sort("ts",-1).limit(limit))