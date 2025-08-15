# backend/src/controllers/poi_controller.py
from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from bson import ObjectId, errors as bson_errors
import logging

from ..models import poi as poi_model
from ..models import poi_doc as poi_doc_model
from ..services.osm_service import fetch_nearby_osm
from ..infra.db import pois
from ..services.wiki_service import fetch_and_store_wiki, find_wikipedia_title
from ..services.poi_enrichment import enrich_poi_list
import asyncio


# Setup logger
logger = logging.getLogger("poi_controller")
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/poi", tags=["poi"])


def _shortid(objid):
    """Helper to shorten ObjectId for logging."""
    return str(objid)[-6:]

@router.get("/{poi_id}")
def get_poi(poi_id: str):
    doc = poi_model.get(poi_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    out = {**doc, "_id": str(doc["_id"])}
    for k in ("created_at", "updated_at", "last_refresh_at"):
        if out.get(k) and hasattr(out[k], "isoformat"):
            out[k] = out[k].isoformat()
    return out

@router.post("/{poi_id}/hydrate")
async def hydrate_poi(poi_id: str, prefer_lang: str = Query("it")):
    try:
        _ = ObjectId(poi_id)
    except bson_errors.InvalidId:
        return JSONResponse(status_code=400, content={"ok": False, "error": "invalid_poi_id"})

    p = poi_model.get(poi_id)
    logger.debug("[hydrate_poi] Loaded POI %s: %s", poi_id, p)
    if not p:
        return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})

    wp = p.get("wikipedia") or {}
    if not wp:
        return {"ok": False, "error": "no_wikipedia_link"}

    try:
        ok = await fetch_and_store_wiki(p, prefer_lang=prefer_lang)
        return {"ok": bool(ok)}
    except Exception as e:
        return JSONResponse(status_code=502, content={"ok": False, "error": "wiki_fetch_failed", "detail": str(e)[:200]})

@router.get("/{poi_id}/docs")
def get_poi_docs(poi_id: str, lang: str | None = None, limit: int = 5):
    try:
        _ = ObjectId(poi_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid poi_id")
    items = poi_doc_model.list_by_poi(poi_id, lang=lang, limit=limit)
    return {"items": items}


@router.post("/nearby")
async def nearby_poi(
    payload: dict = Body(...),
    enrich: bool = Query(default=False),
    max_inserts: int = Query(default=50)
):
    import time
    t0 = time.time()

    lat = payload.get("lat")
    lon = payload.get("lon")
    radius_m = payload.get("radius_m", 50)
    lang = (payload.get("lang") or "it").lower()

    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="lat/lon required")

    logger.debug(f"[nearby_poi] Fetching OSM data lat={lat}, lon={lon}, radius={radius_m}")
    pois_list = await fetch_nearby_osm(lat, lon, radius_m)
    logger.debug(f"[nearby_poi] OSM fetched {len(pois_list)} items in {time.time()-t0:.2f}s")

    inserted = updated = 0
    now = datetime.now(timezone.utc)

    # Garantiamo _id a tutti i POI e inseriamo in DB se nuovi
    for p in pois_list[:max_inserts]:
        if "_id" not in p or not p["_id"]:
            p["_id"] = ObjectId()

        if "osm" in p and "id" in p["osm"]:
            p["osm"]["id"] = str(p["osm"]["id"])
        if not p.get("wikidata_qid"):
            p.pop("wikidata_qid", None)
        if not p.get("langs"):
            p["langs"] = [lang]
        if "last_refresh_at" not in p:
            p["last_refresh_at"] = now
        
        res = pois.update_one(
            {"_id": p["_id"]},
            {"$setOnInsert": {**p, "created_at": now}},
            upsert=True
        )
        if res.upserted_id:
            inserted += 1
        elif res.modified_count:
            updated += 1

    logger.debug(f"[nearby_poi] Inserted={inserted}, Updated={updated} in {time.time()-t0:.2f}s")

    if enrich:
        t_enrich = time.time()
        enriched_results = await enrich_poi_list(pois_list[:max_inserts], lang, write_to_db=False)

        # Aggiorna in background il DB
        asyncio.create_task(enrich_poi_list(enriched_results, lang, write_to_db=True))

        # Usa i risultati arricchiti per la risposta
        pois_list[:max_inserts] = enriched_results
        logger.debug(f"[nearby_poi] Enrichment done in {time.time()-t_enrich:.2f}s")


        # Restituisco lista arricchita subito
        return {
            "attempted": True,
            "fetched": len(pois_list),
            "inserted": inserted,
            "updated": updated,
            "elapsed_sec": round(time.time()-t0, 2),
            "items": [
                {
                    "poi_id": str(p["_id"]),
                    "name": p.get("name"),
                    "wiki_title": p.get("wiki_title"),
                    "wiki_content": p.get("wiki_content"),
                    "distance_m": p.get("distance_m")
                }
                for p in enriched_results
            ]
        }

    # Caso enrich=False → come prima
    return {
        "attempted": True,
        "fetched": len(pois_list),
        "inserted": inserted,
        "updated": updated,
        "elapsed_sec": round(time.time()-t0, 2),
        "items": [
            {
                "poi_id": str(p["_id"]),
                "name": p.get("name"),
                "wiki_title": p.get("wiki_title"),
                "distance_m": p.get("distance_m")
            }
            for p in pois_list[:max_inserts]
        ]
    }

