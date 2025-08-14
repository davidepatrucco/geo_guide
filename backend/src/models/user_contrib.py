from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from ..infra.db import user_contrib

def ensure_indexes():
    user_contrib.create_index([("poi_id", ASCENDING), ("created_at", DESCENDING)], name="poi_created")
    user_contrib.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="status_created")
    user_contrib.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created", sparse=True)

def _oid(x): return x if isinstance(x, ObjectId) else ObjectId(x)

def post(poi_id, text, lang, user_id=None):
    now=datetime.now(timezone.utc)
    doc={"poi_id":_oid(poi_id),"user_id":user_id,"lang":lang,"text":text,"status":"pending","created_at":now,"updated_at":now}
    doc["_id"]=user_contrib.insert_one(doc).inserted_id; return doc
def list_for_poi(poi_id, status=None, limit=100):
    q={"poi_id":_oid(poi_id)}; 
    if status: q["status"]=status
    return list(user_contrib.find(q).sort("created_at",-1).limit(limit))
def list_for_user(user_id, limit=100):
    return list(user_contrib.find({"user_id":user_id}).sort("created_at",-1).limit(limit))
def moderate(contrib_id, status):
    return user_contrib.find_one_and_update({"_id":_oid(contrib_id)}, {"$set":{"status":status,"updated_at":datetime.utcnow()}}, return_document=True)
def delete(contrib_id): return user_contrib.delete_one({"_id":_oid(contrib_id)}).deleted_count