from fastapi import APIRouter, HTTPException, Body, Path
from ..infra.settings import get_settings
from ..models.schemas import POIDetail
from ..utils.validators import ensure_locale, oid
from ..models import poi as poi_model

router = APIRouter(prefix="/poi", tags=["POI"])

@router.post("/nearby")
def nearby(payload: dict = Body(...)) -> dict:
    s = get_settings()
    try:
        lat = float(payload["lat"]); lon = float(payload["lon"])
        radius = int(payload.get("radius_m", s.POI_DEFAULT_RADIUS_M))
        lang = ensure_locale(payload.get("lang","en"))
    except Exception:
        raise HTTPException(status_code=400, detail="Bad request")
    items = poi_model.nearby(lat, lon, radius, lang, limit=10)
    return {"items": items}

@router.get("/{poi_id}", response_model=POIDetail)
def get_poi(poi_id: str = Path(...)):
    doc = poi_model.get(poi_id)
    if not doc:
        raise HTTPException(404, "Not found")
    out = {**doc}
    out["_id"] = str(out["_id"])
    for k in ("created_at","updated_at","last_refresh_at"):
        if out.get(k) and hasattr(out[k], "isoformat"):
            out[k] = out[k].isoformat()
    return out