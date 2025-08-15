from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from ..infra.db import poi_docs

def ensure_indexes():
    poi_docs.create_index([("poi_id", ASCENDING)], name="poi_id")
    poi_docs.create_index([("poi_id", ASCENDING), ("lang", ASCENDING)], name="poi_lang")
    poi_docs.create_index([("created_at", DESCENDING)], name="created_at_desc")
    poi_docs.create_index([("source", ASCENDING)], name="source")

def _oid(x): return x if isinstance(x, ObjectId) else ObjectId(x)

def _ser(doc: dict) -> dict:
    d = dict(doc)
    if "poi_id" in d:
        d["poi_id"] = str(d["poi_id"])
    if "updated_at" in d and hasattr(d["updated_at"], "isoformat"):
        d["updated_at"] = d["updated_at"].isoformat().replace("+00:00", "Z")
    return d

def list_by_poi(poi_id: str, lang: str | None = None, limit: int = 5):
    q = {"poi_id": ObjectId(poi_id)}
    if lang:
        q["lang"] = lang
    proj = {"_id": 0, "poi_id": 1, "lang": 1, "source": 1, "url": 1, "content_text": 1, "updated_at": 1}
    cur = poi_docs.find(q, proj).sort("updated_at", -1).limit(limit)
    return [ _ser(x) for x in cur ]

def insert(poi_id, source, lang, content_text, url=None, meta=None):
    doc={"poi_id":_oid(poi_id),"source":source,"lang":lang,"content_text":content_text,"url":url,"meta":meta or {}, "created_at":datetime.now(timezone.utc)}
    return poi_docs.insert_one(doc).inserted_id

def delete_for_poi(poi_id): return poi_docs.delete_many({"poi_id": _oid(poi_id)}).deleted_count