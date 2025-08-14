from fastapi import APIRouter
from ..models import app_config as appcfg_model

router = APIRouter(tags=["Config"])

@router.get("/config")
def get_config():
    doc = appcfg_model.get_latest() or {}
    if not doc: return {}
    d = {**doc}
    d["_id"] = str(d["_id"])
    if d.get("updated_at") and hasattr(d["updated_at"], "isoformat"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d