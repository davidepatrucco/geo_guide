import httpx, re
from datetime import datetime, timezone
from typing import Optional, Tuple
from ..infra.db import poi_docs
import urllib.parse
import reverse_geocoder as rg
import logging
logger = logging.getLogger(__name__)    

UA = {"User-Agent": "geo-guide/1.0 (+repo-local)"}

def _clean_text(t: str, limit: int = 16000) -> str:
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()[:limit]

async def _query_extracts(lang: str, title: str):
    import httpx
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": True,
        "titles": title,
        "format": "json",
        "redirects": 1
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            logger.warning(f"[wiki] {lang} {title} HTTP {r.status_code} - {r.text[:200]}")
            return None, None, None

        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            logger.warning(f"[wiki] {lang} {title} - empty pages: {data}")
            return None, None, None

        for _, p in pages.items():
            extract = p.get("extract")
            if not extract:
                logger.warning(f"[wiki] {lang} {title} - no extract: {p}")
                return p.get("title"), None, None
            return p.get("title"), p.get("pageid"), extract

    return None, None, None

async def find_wikipedia_title(name: str, lang: str = "en", coords: Optional[Tuple[float, float]] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Cerca su Wikipedia il titolo più vicino al nome fornito.
    Priorità: lingua rilevata da coords → lingua passata → 'en'.
    Fermati al primo match valido.
    """
    if not name:
        return None, None

    detected_lang = None
    if coords is not None:
        try:
            lat, lon = coords
            results = rg.search((lat, lon), mode=1)
            if results and isinstance(results, list):
                country_code = results[0].get('cc', '').upper()
                cc_to_lang = {
                    'DE': 'de', 'AT': 'de', 'CH': 'de',
                    'IT': 'it', 'SM': 'it', 'VA': 'it',
                    'FR': 'fr', 'MC': 'fr', 'BE': 'fr', 'LU': 'fr',
                    'ES': 'es', 'MX': 'es', 'AR': 'es', 'CO': 'es', 'CL': 'es', 'PE': 'es', 'VE': 'es', 'UY': 'es', 'PY': 'es', 'BO': 'es', 'EC': 'es', 'CR': 'es', 'GT': 'es', 'HN': 'es', 'NI': 'es', 'SV': 'es', 'PA': 'es', 'DO': 'es', 'CU': 'es', 'PR': 'es',
                    'PT': 'pt', 'BR': 'pt', 'AO': 'pt', 'MZ': 'pt',
                    'RU': 'ru', 'BY': 'ru', 'KZ': 'ru',
                    'CN': 'zh', 'TW': 'zh', 'HK': 'zh', 'MO': 'zh',
                    'JP': 'ja',
                    'KR': 'ko',
                    'TH': 'th',
                    'VN': 'vi',
                    'TR': 'tr',
                    'GR': 'el',
                    'PL': 'pl',
                    'CZ': 'cs',
                    'SK': 'sk',
                    'HU': 'hu',
                    'RO': 'ro',
                    'BG': 'bg',
                    'FI': 'fi',
                    'SE': 'sv',
                    'NO': 'no',
                    'DK': 'da',
                    'IS': 'is',
                    'IL': 'he',
                    'AE': 'ar', 'SA': 'ar', 'EG': 'ar', 'DZ': 'ar', 'MA': 'ar', 'TN': 'ar', 'JO': 'ar', 'LB': 'ar', 'SY': 'ar', 'YE': 'ar', 'IQ': 'ar', 'KW': 'ar', 'QA': 'ar', 'OM': 'ar', 'BH': 'ar',
                    'IN': 'hi', 'PK': 'ur', 'BD': 'bn', 'NP': 'ne', 'LK': 'si',
                    'GB': 'en', 'UK': 'en', 'IE': 'en', 'US': 'en', 'CA': 'en', 'AU': 'en', 'NZ': 'en', 'ZA': 'en',
                }
                detected_lang = cc_to_lang.get(country_code, 'en')
        except Exception:
            pass

    langs_to_try = []
    for candidate in [detected_lang, lang, "en"]:
        if candidate and candidate not in langs_to_try:
            langs_to_try.append(candidate)

    async with httpx.AsyncClient(timeout=8, headers=UA) as hx:
        for L in langs_to_try:
            api = f"https://{L}.wikipedia.org/w/api.php"

            # 1) Exact match
            exact_params = {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "redirects": "1",
                "prop": "info",
                "titles": name,
            }
            r = await hx.get(api, params=exact_params)
            r.raise_for_status()
            pages = ((r.json().get("query") or {}).get("pages") or [])
            if pages and "missing" not in pages[0]:
                return pages[0]["title"], L

            # 2) Nearmatch solo se exact fallisce
            search_params = {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "list": "search",
                "srsearch": name,
                "srwhat": "nearmatch",
                "srnamespace": 0,
                "srlimit": 1,
            }
            r = await hx.get(api, params=search_params)
            r.raise_for_status()
            hits = ((r.json().get("query") or {}).get("search") or [])
            if hits:
                return hits[0]["title"], L

    return None, None

async def fetch_and_store_wiki(poi: dict, prefer_lang: str = "it") -> bool:
    wp = poi.get("wikipedia") or {}
    lang = prefer_lang if prefer_lang in wp else (next(iter(wp.keys()), None))
    if not lang:
        return False
    wanted = wp[lang]

    found_title, found_lang = await find_wikipedia_title(wanted, lang=lang)
    if not found_title:
        return False

    langs_to_try = [found_lang] if found_lang else []
    if "en" not in langs_to_try:
        langs_to_try.append("en")

    for L in langs_to_try:
        title_to_use = found_title if L == found_lang else wanted
        title, extract_intro, extract_full = await _query_extracts(L, title_to_use)
        if title and extract_full:
            now = datetime.now(timezone.utc)
            poi_docs.update_one(
                {"poi_id": poi["_id"], "source": "wikipedia", "lang": L},
                {"$set": {
                    "url": f"https://{L}.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "context_text": _clean_text(extract_intro, limit=2000),
                    "content_text": _clean_text(extract_full, limit=16000),
                    "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True
            )
            return True
    return False