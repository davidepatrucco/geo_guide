from fastapi import APIRouter, Body, HTTPException, Query
from bson import ObjectId
from datetime import datetime, timezone
from ..models import poi as poi_model
from ..services.narration_service import generate as narr_generate

router = APIRouter(prefix="/narration", tags=["narration"])

@router.post("")
async def create_narration(
    payload: dict = Body(...),
    cache: bool = Query(default=True, description="Se false, forza rigenerazione bypassando cache")
):
    poi_id = payload.get("poi_id")
    lang = (payload.get("lang") or "it").lower()
    style = (payload.get("style") or "guide").lower()
    

    try:
        _ = ObjectId(poi_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid poi_id")

    p = poi_model.get(poi_id)
    if not p:
        raise HTTPException(status_code=404, detail="POI not found")

    out = await narr_generate(p, lang=lang, style=style, cache=cache)

    # log minimale (non blocca)
    try:
        from ..models import usage_log as ulog
        ulog.log({
            "event": "narration.generated",
            "ts": datetime.now(timezone.utc),
            "poi_id": poi_id,
            "lang": lang,
            "style": style,
            "cached": out.get("from_cache", False)
        })
    except Exception:
        pass

    return {"text": out["text"], "cached": out.get("from_cache", False)}