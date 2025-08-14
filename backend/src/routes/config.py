from fastapi import APIRouter, HTTPException
from ..infra.db import app_config

router = APIRouter(prefix="/config", tags=["Config"])

@router.get("")
def get_config():
    doc = app_config.find_one({}, sort=[("version",-1)]) or {}
    if not doc: return {}
    d = {**doc}
    d["_id"] = str(d["_id"])
    if "updated_at" in d and hasattr(d["updated_at"], "isoformat"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d