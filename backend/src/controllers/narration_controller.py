from fastapi import APIRouter, HTTPException
from ..models.schemas import NarrationRequest, NarrationResponse
from ..utils.validators import oid, ensure_locale
from ..services.agents.graph import run_pipeline
from ..models import narration_cache as cache_model

router = APIRouter(prefix="/narration", tags=["Narration"])

@router.post("", response_model=NarrationResponse)
def create_or_get(req: NarrationRequest):
    poi_oid = oid(req.poi_id); ensure_locale(req.lang)
    cached = cache_model.get(poi_oid, req.lang, req.style)
    if cached:
        return {
            "poi_id": str(poi_oid), "style": req.style, "lang": req.lang,
            "text": cached["text"], "audio_url": cached.get("audio_url"),
            "sources": cached["sources"], "confidence": float(cached.get("confidence",0.8))
        }
    text, sources, conf = run_pipeline(str(poi_oid), req.lang, req.style)
    doc = cache_model.upsert(poi_oid, req.lang, req.style, text, sources, audio_url=None, confidence=conf)
    return {
        "poi_id": str(poi_oid), "style": req.style, "lang": req.lang,
        "text": doc["text"], "audio_url": doc.get("audio_url"),
        "sources": doc["sources"], "confidence": float(doc.get("confidence",conf))
    }

@router.get("/{poi_id}/{lang}/{style}", response_model=NarrationResponse)
def get_from_cache(poi_id: str, lang: str, style: str):
    poi_oid = oid(poi_id); ensure_locale(lang)
    cached = cache_model.get(poi_oid, lang, style)
    if not cached:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "poi_id": poi_id, "style": style, "lang": lang,
        "text": cached["text"], "audio_url": cached.get("audio_url"),
        "sources": cached["sources"], "confidence": float(cached.get("confidence",0.8))
    }