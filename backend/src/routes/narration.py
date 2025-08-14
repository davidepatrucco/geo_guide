from fastapi import APIRouter, HTTPException, Path
from datetime import datetime, timezone
from pymongo import ReturnDocument
from ..infra.db import narrations_cache
from ..models.schemas import NarrationRequest, NarrationResponse
from ..utils.validators import oid, ensure_locale
from ..services.agents.graph import run_pipeline

router = APIRouter(prefix="/narration", tags=["Narration"])

@router.post("", response_model=NarrationResponse)
def create_or_get(req: NarrationRequest):
    poi_id = oid(req.poi_id)
    # tenta cache
    cached = narrations_cache.find_one({"poi_id": poi_id, "lang": req.lang, "style": req.style})
    if cached:
        return {
            "poi_id": req.poi_id, "style": req.style, "lang": req.lang,
            "text": cached["text"], "audio_url": cached.get("audio_url"),
            "sources": cached["sources"], "confidence": float(cached.get("confidence",0.8))
        }
    # pipeline
    text, sources, conf = run_pipeline(str(poi_id), req.lang, req.style)
    doc = {
        "poi_id": poi_id, "style": req.style, "lang": req.lang,
        "text": text, "audio_url": None, "sources": sources,
        "confidence": float(conf), "created_at": datetime.now(timezone.utc)
    }
    narrations_cache.find_one_and_update(
        {"poi_id": poi_id, "lang": req.lang, "style": req.style},
        {"$setOnInsert": doc}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return {
        "poi_id": str(poi_id), "style": req.style, "lang": req.lang,
        "text": text, "audio_url": None, "sources": sources, "confidence": conf
    }

@router.get("/{poi_id}/{lang}/{style}", response_model=NarrationResponse)
def get_from_cache(poi_id: str, lang: str, style: str):
    poi_oid = oid(poi_id); ensure_locale(lang)
    cached = narrations_cache.find_one({"poi_id": poi_oid, "lang": lang, "style": style})
    if not cached:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "poi_id": poi_id, "style": style, "lang": lang,
        "text": cached["text"], "audio_url": cached.get("audio_url"),
        "sources": cached["sources"], "confidence": float(cached.get("confidence",0.8))
    }