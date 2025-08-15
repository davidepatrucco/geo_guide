import httpx, math

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_QUERY = """
[out:json][timeout:25];
(
  node(around:{rad},{lat},{lon})[name];
  way(around:{rad},{lat},{lon})[name];
  relation(around:{rad},{lat},{lon})[name];
);
out tags center;
"""

def _dist_m(lat1, lon1, lat2, lon2):
    R=6371000
    p=math.pi/180
    dlat=(lat2-lat1)*p; dlon=(lon2-lon1)*p
    a=math.sin(dlat/2)**2+math.cos(lat1*p)*math.cos(lat2*p)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

async def fetch_nearby_osm(lat: float, lon: float, rad: int = 250, **kwargs):
    limit = kwargs.get("limit", 200)
    max_keep = kwargs.get("max_keep", 200)

    q = OSM_QUERY.format(lat=lat, lon=lon, rad=rad)
    headers = {"User-Agent": "geo-guide/1.0 (+https://example.com)"}
    async with httpx.AsyncClient(timeout=25) as hx:
        r = await hx.post(OVERPASS_URL, data=q, headers=headers)
        r.raise_for_status()
        data = r.json()

    items = []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        lat0 = el.get("lat") or (el.get("center") or {}).get("lat")
        lon0 = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat0 is None or lon0 is None:
            continue
        wiki = tags.get("wikipedia")
        wiki_lang, wiki_title = (wiki.split(":",1) if wiki and ":" in wiki else (None,None))
        dist = _dist_m(lat, lon, float(lat0), float(lon0))
        items.append({
            "source": "osm",
            "osm": {"type": el.get("type"), "id": el.get("id")},
            "name": {"default": name},
            "aliases": [],
            "location": {"type":"Point","coordinates":[float(lon0), float(lat0)]},
            "wikidata_qid": tags.get("wikidata"),
            "wikipedia": {wiki_lang: wiki_title} if wiki_lang and wiki_title else {},
            "langs": [wiki_lang] if wiki_lang else [],
            "photos": [],
            "_distance_m": dist,
        })

    # ordina per distanza e tieni i più vicini
    items.sort(key=lambda x: x["_distance_m"])
    return items[:max_keep]