from fastapi import APIRouter, HTTPException, Body
from ..models.schemas import ContribPostRequest, ContribItem
from ..utils.validators import oid, ensure_locale
from ..models import user_contrib as contrib_model

router = APIRouter(prefix="/contrib", tags=["Contrib"])

@router.post("", response_model=ContribItem, status_code=201)
def post_contrib(req: ContribPostRequest):
    poi_oid = oid(req.poi_id); ensure_locale(req.lang)
    doc = contrib_model.post(poi_oid, req.text, req.lang, user_id=None)
    return {
        "_id": str(doc["_id"]), "poi_id": str(doc["poi_id"]), "lang": doc["lang"],
        "text": doc["text"], "status": doc["status"], "created_at": doc["created_at"].isoformat()
    }

@router.get("/{poi_id}")
def list_contrib(poi_id: str, status: str | None = None):
    items = []
    for c in contrib_model.list_for_poi(oid(poi_id), status=status):
        items.append({
            "_id": str(c["_id"]), "poi_id": str(c["poi_id"]), "lang": c["lang"],
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
    upd = contrib_model.moderate(id, status)
    if not upd: raise HTTPException(status_code=404, detail="Not found")
    return {
        "_id": str(upd["_id"]), "poi_id": str(upd["poi_id"]), "lang": upd["lang"],
        "text": upd["text"], "status": upd["status"],
        "created_at": upd["created_at"].isoformat(),
        "updated_at": upd.get("updated_at") and upd["updated_at"].isoformat()
    }