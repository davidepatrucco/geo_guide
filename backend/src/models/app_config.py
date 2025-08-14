from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from ..infra.db import app_config

def ensure_indexes():
    app_config.create_index([("_id", ASCENDING)], name="pk", unique=True)
    app_config.create_index([("version", DESCENDING)], name="version_desc")

def get_latest():
    return app_config.find_one({}, sort=[("version",-1)])

def upsert(_id: str, version: int, flags: dict, limits: dict, llm: dict | None = None):
    doc={"_id":_id,"version":version,"flags":flags,"limits":limits,"llm":llm or {}, "updated_at": datetime.now(timezone.utc)}
    return app_config.find_one_and_update({"_id":_id}, {"$set": doc}, upsert=True, return_document=ReturnDocument.AFTER)