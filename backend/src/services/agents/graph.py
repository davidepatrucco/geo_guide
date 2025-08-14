# pipeline minimale: researcher -> curator -> narrator (testo-only)
from ...infra.db import poi_docs
from ...infra.settings import get_settings
from bson import ObjectId

def _collect_docs(poi_id: str, lang: str) -> list[dict]:
    q = {"poi_id": ObjectId(poi_id)}
    docs = list(poi_docs.find(q, {"_id":0, "source":1, "url":1, "lang":1, "content_text":1}))
    prefers = [d for d in docs if d.get("lang")==lang] or docs
    return prefers

def _synthesize_text(docs: list[dict], lang: str, style: str) -> tuple[str, list[dict], float]:
    if not docs:
        return ("Nessuna fonte disponibile per questo POI.", [], 0.3)
    settings = get_settings()
    joined = " ".join((d.get("content_text") or "")[:400] for d in docs[:3])
    text = joined[:settings.NARRATION_MAX_CHARS].strip()
    sources = [{"name": d["source"], "url": d.get("url","https://example.com")} for d in docs[:3] if d.get("source")]
    confidence = 0.8 if len(docs) >= 2 else 0.5
    if style == "kids": text = "🧒 " + text
    elif style == "quick": text = "In breve: " + text
    elif style == "anecdotes": text = "Curiosità: " + text
    return text, sources, confidence

def run_pipeline(poi_id: str, lang: str, style: str) -> tuple[str, list[dict], float]:
    docs = _collect_docs(poi_id, lang)
    return _synthesize_text(docs, lang, style)