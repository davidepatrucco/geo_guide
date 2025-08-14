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

def list_by_poi(poi_id, lang=None, limit=20):
    q={"poi_id":_oid(poi_id)}; 
    if lang: q["lang"]=lang
    return list(poi_docs.find(q).sort("created_at",-1).limit(limit))
def insert(poi_id, source, lang, content_text, url=None, meta=None):
    doc={"poi_id":_oid(poi_id),"source":source,"lang":lang,"content_text":content_text,"url":url,"meta":meta or {}, "created_at":datetime.now(timezone.utc)}
    return poi_docs.insert_one(doc).inserted_id
def delete_for_poi(poi_id): return poi_docs.delete_many({"poi_id": _oid(poi_id)}).deleted_count