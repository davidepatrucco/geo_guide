from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ASCENDING
from ..infra.db import narrations_cache

TTL_SECONDS = 24*3600

def ensure_indexes():
    narrations_cache.create_index([("poi_id", ASCENDING), ("lang", ASCENDING), ("style", ASCENDING)],
                                  name="uq_poi_lang_style", unique=True)
    try:
        narrations_cache.create_index([("created_at", ASCENDING)], name="ttl_created_at", expireAfterSeconds=TTL_SECONDS)
    except Exception:
        pass

def _oid(x): 
    return x if isinstance(x, ObjectId) else ObjectId(x)

def get(poi_id, lang, style):
    return narrations_cache.find_one({"poi_id": _oid(poi_id), "lang": lang, "style": style})
def upsert(poi_id, lang, style, text, sources, audio_url=None, confidence=0.8):
    doc={"poi_id":_oid(poi_id),"lang":lang,"style":style,"text":text,"sources":sources,
         "audio_url":audio_url,"confidence":float(confidence),"created_at":datetime.now(timezone.utc)}
    narrations_cache.update_one({"poi_id":doc["poi_id"],"lang":lang,"style":style}, {"$setOnInsert": doc}, upsert=True)
    return doc
def invalidate(poi_id=None):
    if poi_id: return narrations_cache.delete_many({"poi_id": _oid(poi_id)}).deleted_count
    return narrations_cache.delete_many({}).deleted_count