from fastapi import APIRouter, Body
from datetime import datetime, timedelta
import logging
from bson import ObjectId
from difflib import SequenceMatcher

from ..infra.db import pois, poi_docs, searched_pois
from ..services.osm_service import fetch_osm_pois
from ..services.wiki_service import fetch_wiki_docs
import reverse_geocoder as rg

router = APIRouter()

SEARCH_TTL_DAYS = 5
COORD_PRECISION = 6
POI_RADIUS_METERS = 200

def serialize_doc(doc):
    """Converte ObjectId in stringhe per la serializzazione JSON."""
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    if "poi_id" in doc and isinstance(doc["poi_id"], ObjectId):
        doc["poi_id"] = str(doc["poi_id"])
    return doc

def get_lang_from_coords(lat, lon):
    result = rg.search((lat, lon))[0]
    country_code = result['cc']
    country_lang_map = {
        "IT": "it",
        "FR": "fr",
        "DE": "de",
        "US": "en",
    }
    return country_lang_map.get(country_code, "en")

def round_coord(lat, lon):
    return (round(lat, COORD_PRECISION), round(lon, COORD_PRECISION))

def is_relevant_name(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """Verifica se due nomi sono molto simili."""
    if not name1 or not name2:
        return False
    n1, n2 = name1.lower().strip(), name2.lower().strip()
    if n1 == n2:
        return True
    return SequenceMatcher(None, n1, n2).ratio() >= threshold

@router.post("/nearby")
async def get_nearby_pois(payload: dict = Body(...)):
    lat = payload["lat"]
    lon = payload["lon"]
    radius_m = payload.get("radius", POI_RADIUS_METERS)
    enrich = payload.get("enrich", False)

    req_lang = get_lang_from_coords(lat, lon)
    logging.info(f"[NEARBY] Request for lat={lat}, lon={lon}, enrich={enrich}, lang={req_lang}")

    now = datetime.utcnow()
    lat_r, lon_r = round_coord(lat, lon)

    # Cache hit
    search_entry = searched_pois.find_one({"lat": lat_r, "lon": lon_r})
    if search_entry and search_entry["last_search_at"] >= now - timedelta(days=SEARCH_TTL_DAYS):
        pois_list = [serialize_doc(p) for p in pois.find({
            "location": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "$maxDistance": radius_m
                }
            },
            "is_active": True
        })]
        poi_ids = [ObjectId(p["_id"]) for p in pois_list]
        docs_list = [serialize_doc(d) for d in poi_docs.find({"poi_id": {"$in": poi_ids}})]
        return {"source": "cache", "pois": pois_list, "docs": docs_list}

    # Step 1: Fetch OSM
    osm_pois = await fetch_osm_pois(lat, lon, radius_m)

    found_ids = []
    seen_names = []

    for osm_poi in osm_pois:
        name = osm_poi.get("name", "").strip()
        if not name or len(name) < 3:
            continue
        if any(is_relevant_name(name, seen) for seen in seen_names):
            logging.debug(f"[NEARBY] Skipping duplicate/similar POI name '{name}'")
            continue
        seen_names.append(name)

        lat_r_poi, lon_r_poi = round_coord(osm_poi["lat"], osm_poi["lon"])
        existing = pois.find_one({
            "lat_round": lat_r_poi,
            "lon_round": lon_r_poi,
            "provider": "osm",
            "provider_id": osm_poi.get("id")
        })

        if existing:
            pois.update_one(
                {"_id": existing["_id"]},
                {"$set": {"last_seen_at": now, "is_active": True}}
            )
            poi_id = existing["_id"]
        else:
            poi_id = pois.insert_one({
                "lat_round": lat_r_poi,
                "lon_round": lon_r_poi,
                "provider": "osm",
                "provider_id": osm_poi.get("id"),
                "name": {"default": name},
                "aliases": [],
                "location": {
                    "type": "Point",
                    "coordinates": [osm_poi["lon"], osm_poi["lat"]]
                },
                "langs": [req_lang],
                "photos": [],
                "last_seen_at": now,
                "is_active": True,
                "created_at": now,
                "updated_at": now
            }).inserted_id
        found_ids.append(poi_id)

    # Disattiva POI fuori raggio
    pois.update_many(
        {
            "location": {
                "$geoWithin": {
                    "$centerSphere": [[lon, lat], radius_m / 6378137]
                }
            },
            "_id": {"$nin": found_ids}
        },
        {"$set": {"is_active": False}}
    )

    # Step 2: Enrichment Wikipedia
    if enrich:
        for poi_id in found_ids:
            poi = pois.find_one({"_id": poi_id})
            docs = await fetch_wiki_docs(poi)
            for doc in docs:
                if isinstance(doc.get("poi_id"), str):
                    doc["poi_id"] = ObjectId(doc["poi_id"])
                poi_docs.update_one(
                    {
                        "poi_id": poi_id,
                        "lang": doc["lang"],
                        "source": "wikipedia",
                        "url": doc["url"]
                    },
                    {"$set": {**doc, "updated_at": now}},
                    upsert=True
                )

    searched_pois.update_one(
        {"lat_round": lat_r, "lon_round": lon_r},
        {"$set": {"lat_round": lat_r, "lon_round": lon_r, "last_search_at": now}},
        upsert=True
    )

    pois_list = [serialize_doc(p) for p in pois.find({"_id": {"$in": found_ids}})]
    docs_list = [serialize_doc(d) for d in poi_docs.find({"poi_id": {"$in": found_ids}})]

    return {"source": "fresh", "pois": pois_list, "docs": docs_list}