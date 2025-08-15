# backend/src/services/poi_enrichment.py
import asyncio
import httpx
from datetime import datetime, timezone
from ..infra.db import pois, poi_docs
from .wiki_service import _clean_text
from . import wiki_service
from pymongo import UpdateOne
from bson import ObjectId

import reverse_geocoder


UA = {"User-Agent": "geo-guide/1.0 (+repo-local)"}

country_lang_map = {
    "DE": "de",
    "IT": "it",
    "FR": "fr",
    "CH": "de",
}

def lang_from_coords(lat, lon, default="en"):
    
    results = reverse_geocoder.search((lat, lon))
    if results:
        cc = results[0].get("cc")
        return country_lang_map.get(cc, default)
    return default

async def guess_wikipedia_title(name: str, lang: str = "it") -> str | None:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": name,
        "srlimit": 1
    }
    async with httpx.AsyncClient(timeout=5, headers=UA) as hx:
        r = await hx.get(api, params=params)
        r.raise_for_status()
        hits = r.json().get("query", {}).get("search", [])
        if hits:
            return hits[0]["title"]
    return None

async def fetch_wikipedia_content(title: str, lang: str = "it") -> str | None:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
        "prop": "extracts",
        "explaintext": "1",
        # tolto exintro per prendere tutto il testo
        "titles": title,
    }
    async with httpx.AsyncClient(timeout=8, headers=UA) as hx:
        r = await hx.get(api, params=params)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", [])
        if pages and "missing" not in pages[0]:
            return _clean_text(pages[0].get("extract", ""))
    return None

async def enrich_poi(poi: dict, lang: str = "it") -> dict:
    wiki_title = poi.get("wiki_title")
    if not wiki_title and poi.get("name"):
        wiki_title = await guess_wikipedia_title(poi["name"], lang)
    content = None
    if wiki_title:
        content = await fetch_wikipedia_content(wiki_title, lang)
    return {
        "_id": poi["_id"],
        "wiki_title": wiki_title,
        "wiki_content": content
    }

import re
from datetime import datetime, timezone
import asyncio
from src.services.wiki_service import find_wikipedia_title, _query_extracts
from src.infra.db import pois  # usa direttamente la collection

import logging
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import UpdateOne

logger = logging.getLogger(__name__)

async def enrich_poi_list(pois_list: list[dict], lang: str = "en", write_to_db: bool = True):
    logger.info(f"[enrich_poi_list] START: {len(pois_list)} POIs, lang={lang}, write_to_db={write_to_db}")

    now = datetime.now(timezone.utc)
    results = []

    bulk_pois = []
    bulk_docs = []

    for p in pois_list:
        logger.debug(f"[enrich_poi_list] Processing POI {p.get('_id')}")

        lat = p.get("location", {}).get("coordinates", [None, None])[1]
        lon = p.get("location", {}).get("coordinates", [None, None])[0]

        if lat is not None and lon is not None:
            poi_lang = lang_from_coords(lat, lon, lang)
            logger.debug(f"[enrich_poi_list] Detected language '{poi_lang}' for POI {p.get('_id')}")
        else:
            poi_lang = lang
            logger.debug(f"[enrich_poi_list] Using default lang '{poi_lang}' for POI {p.get('_id')}")

        wiki_title = p.get("wiki_title")
        wiki_content = None
        wiki_url = None

        # Trova titolo Wikipedia se manca
        if not wiki_title and p.get("name"):
            name_str = p["name"].get("default") if isinstance(p.get("name"), dict) else p.get("name")
            found_title, _ = await find_wikipedia_title(name_str, poi_lang)
            if found_title:
                wiki_title = found_title
                logger.info(f"[enrich_poi_list] Found Wikipedia title '{wiki_title}' for POI {p.get('_id')}")
            else:
                logger.debug(f"[enrich_poi_list] No Wikipedia title found for POI {p.get('_id')} ({name_str})")

        # Scarica contenuto se abbiamo titolo
        if wiki_title:
            final_title, _, extract_full = await _query_extracts(poi_lang, wiki_title)
            if extract_full:
                wiki_title = final_title or wiki_title
                wiki_content = extract_full
                wiki_url = f"https://{poi_lang}.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}"
                logger.info(f"[enrich_poi_list] Got content for '{wiki_title}' ({len(wiki_content)} chars) for POI {p.get('_id')}")
            else:
                logger.warning(f"[enrich_poi_list] No content returned for '{wiki_title}' (POI {p.get('_id')})")

        # Aggiungi al risultato
        results.append({
            "_id": p["_id"],
            "poi_lang": poi_lang,
            "wiki_title": wiki_title,
            "wiki_content": wiki_content,
            "wiki_url": wiki_url
        })

        if write_to_db and wiki_title:
            update_fields = {
                f"wikipedia.{poi_lang}": wiki_title,
                "updated_at": now
            }
            if wiki_content:
                update_fields[f"wiki_content.{poi_lang}"] = wiki_content
            bulk_pois.append(UpdateOne({"_id": p["_id"]}, {"$set": update_fields}, upsert=False))
            logger.debug(f"[enrich_poi_list] Added POI update for {p['_id']}")

            if wiki_content and wiki_url and wiki_content.strip():
                bulk_docs.append(UpdateOne(
                    {"poi_id": ObjectId(p["_id"]), "lang": poi_lang},
                    {
                        "$set": {
                            "poi_id": ObjectId(p["_id"]),
                            "lang": poi_lang,
                            "content_text": wiki_content,
                            "source": "wikipedia",
                            "url": wiki_url,
                            "updated_at": now
                        },
                        "$setOnInsert": {"created_at": now}
                    },
                    upsert=True
                ))
                logger.debug(f"[enrich_poi_list] Added poi_docs upsert for {p['_id']} ({len(wiki_content)} chars)")

    if write_to_db:
        if bulk_pois:
            res_pois = pois.bulk_write(bulk_pois)
            logger.info(f"[enrich_poi_list] pois.bulk_write result: {res_pois.bulk_api_result}")
        else:
            logger.debug("[enrich_poi_list] No POI updates to write")

        if bulk_docs:
            res_docs = poi_docs.bulk_write(bulk_docs)
            logger.info(f"[enrich_poi_list] poi_docs.bulk_write result: {res_docs.bulk_api_result}")
        else:
            logger.debug("[enrich_poi_list] No poi_docs upserts to write")

    logger.info(f"[enrich_poi_list] END: processed {len(pois_list)} POIs")
    return results