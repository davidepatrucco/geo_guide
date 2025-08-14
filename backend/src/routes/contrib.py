from fastapi import APIRouter, HTTPException, Body, Path
from datetime import datetime, timezone
from ..infra.db import user_contrib
from ..models.schemas import ContribPostRequest, ContribItem
from ..utils.validators import oid, ensure_locale

router = APIRouter(prefix="/contrib", tags=["Contrib"])

@router.post("", response_model=ContribItem, status_code=201)
def post_contrib(req: ContribPostRequest):
    poi_oid = oid(req.poi_id); ensure_locale(req.lang)
    now = datetime.now(timezone.utc)
    doc = {
        "poi_id": poi_oid, "user_id": None, "lang": req.lang, "text": req.text,
        "status": "pending", "created_at": now, "updated_at": now
    }
    ins = user_contrib.insert_one(doc)
    doc["_id"] = ins.inserted_id
    return {
        "_id": str(doc["_id"]), "poi_id": str(poi_oid), "lang": req.lang,
        "text": req.text, "status":"pending", "created_at": now.isoformat()
    }

@router.get("/{poi_id}")
def list_contrib(poi_id: str, status: str | None = None):
    q = {"poi_id": oid(poi_id)}
    if status: q["status"] = status
    items = []
    for c in user_contrib.find(q).sort("created_at",-1).limit(100):
        items.append({
            "_id": str(c["_id"]), "poi_id": poi_id, "lang": c["lang"],
            "text": c["text"], "status": c["status"],
            "created_at": c["created_at"].isoformat(),
            "updated_at": c.get("updated_at") and c["updated_at"].isoformat()
        })
    return {"items": items}

@router.patch("/{id}", response_model=ContribItem)
def moderate(id: str, payload: dict = Body(...)):
    status = payload.get("status")
    if status not in ("approved","rejected"):
        raise HTTPException(status_code=400, detail="Invalid status")
    upd = user_contrib.find_one_and_update(
        {"_id": oid(id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        return_document=True
    )
    if not upd: raise HTTPException(status_code=404, detail="Not found")
    return {
        "_id": str(upd["_id"]), "poi_id": str(upd["poi_id"]), "lang": upd["lang"],
        "text": upd["text"], "status": upd["status"],
        "created_at": upd["created_at"].isoformat(),
        "updated_at": upd.get("updated_at") and upd["updated_at"].isoformat()
    }