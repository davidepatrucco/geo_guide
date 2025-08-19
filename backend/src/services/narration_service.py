# backend/src/services/narration_service.py
from __future__ import annotations
import os
import re
from datetime import datetime
from typing import Tuple, List
from bson import ObjectId
import json
import httpx
from ..infra.db import poi_docs, narrations_cache
import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_ALLOWED = {"guide", "quick", "kids", "anecdotes"}
_SYNONYMS = {
    "fun": "anecdotes",
    "scholarly": "guide",
    "story": "guide",
    "fast": "quick"
}

def _normalize_style(style: str) -> str:
    s = (style or "guide").lower().strip()
    s = _SYNONYMS.get(s, s)
    return s if s in _ALLOWED else "guide"

# --------- helpers ---------
def _style_preamble(style: str) -> str:
    s = _normalize_style(style)
    mapping = {
        "guide": "Parla come guida locale. Tono chiaro, caldo. anche 500 parole.",
        "fun": "Tono brillante e curioso, con 1 aneddoto. 200-220 parole.",
        "kids": "Spiega per bambini (8–11 anni), semplice e divertente. 100–140 parole.",
        "anecdotes": "Stile enciclopedico e preciso, 200-220 parole, senza enfasi."
    }
    return mapping.get(s, mapping["guide"])

def _clean_text(t: str) -> str:
    t = re.sub(r"\n{3,}", "\n\n", t or "")
    return t.strip()[:4000]

def _build_prompt(name: str, text_src: str | None, style: str, lang: str) -> str:
    base = f"Titolo POI: {name}\nStile: {_style_preamble(style)}\n\n"
    if text_src:
        base += "Materiale disponibile:\n" + _clean_text(text_src) + "\n\n"
    base += (
        f"Scrivi una narrazione conforme allo stile. Rispondi in {lang}. "
        "Evita liste puntate, niente link, niente frasi ridondanti."
    )
    return base

async def _call_openai(prompt: str, lang: str) -> str:
    if not OPENAI_API_KEY:
        body = _clean_text(prompt)
        return (body[-700:] if len(body) > 700 else body) or "Contenuto non disponibile."
    payload = {
        "model": "gpt-5-nano",
        "messages": [
            {"role": "system", "content": f"Rispondi in {lang}. Mantieni il testo entro 400 parole."},
            {"role": "user", "content": prompt}
        ]
    }
    logging.debug(f"OpenAI payload: {payload}")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    async with httpx.AsyncClient(timeout=60) as hx:
        r = await hx.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

def _read_docs(poi_id: str):
    """Ritorna (text_src, sources_list[dict{name,url,...}])."""
    oid = ObjectId(poi_id)
    docs = list(poi_docs.find({"poi_id": oid}, {"content_text": 1, "url": 1, "lang": 1}))

    text_src = None
    sources = []
    for doc in docs:
        if not text_src and doc.get("content_text"):
            text_src = doc["content_text"]
        if doc.get("url"):
            sources.append({
                "name": "wikipedia",
                "url": doc["url"],
                "lang": doc.get("lang", "").lower()
            })
    return text_src, sources

def _cache_key(poi_id: str, lang: str, style: str) -> str:
    return f"{poi_id}:{lang}:{style}"

def _confidence(has_text: bool) -> float:
    return 0.85 if has_text else 0.6

def get_cached(poi_id: str, lang: str, style: str):
    return narrations_cache.find_one({"_id": _cache_key(poi_id, lang, style)})

def set_cached(poi_id: str, lang: str, style: str, text: str, sources: list, conf: float):
    now = datetime.utcnow()
    narrations_cache.update_one(
        {"_id": f"{poi_id}:{lang}:{style}"},
        {"$set": {
            "poi_id": ObjectId(poi_id),
            "lang": lang,
            "style": style,
            "text": text,
            "sources": sources,
            "confidence": float(conf),
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True
    )

# --------- API principale ---------
async def generate(poi: dict, lang: str, style: str, cache: bool = True) -> dict:
    poi_id = str(poi["_id"])
    style_norm = _normalize_style(style)

    if cache:
        cached = get_cached(poi_id, lang, style_norm)
        if cached:
            return {"from_cache": True, "text": cached["text"]}

    name = (poi.get("name") or {}).get(lang) \
        or (poi.get("name") or {}).get("it") \
        or (poi.get("name") or {}).get("en") \
        or "Questo luogo"

    text_src, sources = _read_docs(poi_id)
    logger.debug("[narration.generate] POI %s has_text=%s sources_count=%d",
                 poi_id, bool(text_src), len(sources or []))

    prompt = _build_prompt(name, text_src, style_norm, lang)
    out_text = await _call_openai(prompt, lang)

    conf = _confidence(bool(text_src))
    if not sources:
        logger.warning(f"[narr_generate] No sources for {poi_id}, skipping cache save")
        return {"poi_id": poi_id, "lang": lang, "style": style, "text": out_text, "sources": []}

    set_cached(poi_id, lang, style_norm, out_text, sources or [], conf)
    return {"from_cache": False, "text": out_text}