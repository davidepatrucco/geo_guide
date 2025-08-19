# services/wiki_service.py
import logging
import aiohttp
import certifi
import ssl
from datetime import datetime
from bson import ObjectId
from difflib import SequenceMatcher

WIKI_API_URL = "https://{lang}.wikipedia.org/w/api.php"
ssl_context = ssl.create_default_context(cafile=certifi.where())

def is_relevant(title: str, name: str, threshold: float = 0.8) -> bool:
    title_lower = title.lower()
    name_lower = name.lower()
    if name_lower in title_lower or title_lower in name_lower:
        return True
    return SequenceMatcher(None, title_lower, name_lower).ratio() >= threshold

async def fetch_wiki_docs(poi):
    lang = poi.get("langs", ["en"])[0]
    name = ""
    if isinstance(poi.get("name"), str):
        name = poi["name"]
    elif isinstance(poi.get("name"), dict):
        name = poi["name"].get("default") or next((v for v in poi["name"].values() if v), "")
    name = name.strip()

    if not name:
        logging.warning(f"[WIKI] No valid name for POI {poi.get('_id')}, lang={lang}")
        logging.debug(f"[WIKI] Full POI data: {poi}")
        return []

    logging.info(f"[WIKI] Fetching docs for POI '{name}' in lang={lang}")
    logging.debug(f"[WIKI] Full POI data: {poi}")

    # STEP 1: Search
    params_search = {
        "action": "query",
        "list": "search",
        "srsearch": name,
        "format": "json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(WIKI_API_URL.format(lang=lang), params=params_search, ssl=ssl_context) as resp:
            if resp.status != 200:
                logging.error(f"[WIKI] Search failed for '{name}' (status={resp.status})")
                return []
            search_data = await resp.json()

    search_results = search_data.get("query", {}).get("search", [])
    if not search_results:
        logging.info(f"[WIKI] No search results for '{name}' in lang={lang}")
        return []

    # Filtra risultati pertinenti
    search_results = [r for r in search_results if is_relevant(r["title"], name)]
    if not search_results:
        logging.info(f"[WIKI] No relevant search results for '{name}' in lang={lang}")
        return []

    docs = []
    async with aiohttp.ClientSession() as session:
        for result in search_results:
            page_title = result["title"]
            logging.info(f"[WIKI] Found page title: {page_title}")

            params_extract = {
                "action": "query",
                "prop": "extracts",
                "explaintext": "true",
                "titles": page_title,
                "format": "json"
            }
            async with session.get(WIKI_API_URL.format(lang=lang), params=params_extract, ssl=ssl_context) as resp:
                if resp.status != 200:
                    logging.warning(f"[WIKI] Failed to fetch content for '{page_title}'")
                    continue
                page_data = await resp.json()

            for _, page in page_data.get("query", {}).get("pages", {}).items():
                content = page.get("extract", "").strip()
                if not content:
                    logging.debug(f"[WIKI] Page '{page_title}' has no extract")
                    continue

                docs.append({
                    "poi_id": poi["_id"],  # ObjectId, non stringa
                    "provider": poi.get("provider", "unknown"),
                    "provider_id": poi.get("provider_id"),
                    "source": "wikipedia",
                    "url": f"https://{lang}.wikipedia.org/wiki/{page_title.replace(' ', '_')}",
                    "lang": lang,
                    "content_text": content,
                    "sections": [],
                    "meta": {"title": page_title},
                    "created_at": datetime.utcnow()
                })
                logging.debug(f"[WIKI] Added doc for '{page_title}' ({len(content)} chars)")

    logging.info(f"[WIKI] Total docs for '{name}': {len(docs)}")
    return docs