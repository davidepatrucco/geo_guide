# backend/src/models/poi.py
from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt
from pymongo import ASCENDING, GEOSPHERE
from bson import ObjectId
from ..infra.db import pois

# ---------- indici ----------
def ensure_indexes():
    pois.create_index([("location", GEOSPHERE)], name="geo_location")
    pois.create_index([("wikidata_qid", ASCENDING)], name="wikidata_qid", sparse=True)
    pois.create_index([("wikipedia.it", ASCENDING)], name="wikipedia_it", sparse=True)
    pois.create_index([("name.en", ASCENDING)], name="name_en")
    pois.create_index([("updated_at", ASCENDING)], name="updated_at")

# ---------- utils ----------
def _oid(x): return x if isinstance(x, ObjectId) else ObjectId(x)

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

# ---------- CRUD ----------
def get(poi_id): return pois.find_one({"_id": _oid(poi_id)})
def get_many(ids): return list(pois.find({"_id": {"$in": [_oid(i) for i in ids]}}))

def insert(doc: dict):
    now = datetime.now(timezone.utc)
    doc.setdefault("created_at", now); doc.setdefault("updated_at", now)
    return pois.insert_one(doc).inserted_id

def update(poi_id: str, data: dict):
    data["updated_at"] = datetime.now(timezone.utc)
    return pois.update_one({"_id": _oid(poi_id)}, {"$set": data}).modified_count

def delete(poi_id: str): return pois.delete_one({"_id": _oid(poi_id)}).deleted_count

# ---------- query geospaziale ----------
def nearby(lat: float, lon: float, radius_m: int, lang: str, limit: int = 10):
    q = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                "$maxDistance": radius_m
            }
        }
    }
    items = []
    used_near = True
    try:
        cur = pois.find(q, {"name": 1, "location": 1, "wikipedia": 1}).limit(50)
    except Exception:
        # fallback senza indice geospaziale
        used_near = False
        cur = pois.find({}, {"name": 1, "location": 1, "wikipedia": 1}).limit(300)
    for p in cur:
        coords = p["location"]["coordinates"]
        dist = _haversine(lat, lon, coords[1], coords[0])
        if used_near or dist <= radius_m:
            name = (p.get("name") or {}).get(lang) or (p.get("name") or {}).get("en") or ""
            items.append({
                "poi_id": str(p["_id"]),
                "name": name,
                "distance_m": round(dist, 2),
                "coords": coords,
                "wiki_title": (p.get("wikipedia") or {}).get(lang)
            })
    items.sort(key=lambda x: x["distance_m"])
    return items[:limit]

# ---------- upsert da OSM ----------
def upsert_many_from_osm(docs: list[dict], max_inserts: int = 30) -> dict:
    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc)

    for d in docs:
        if inserted >= max_inserts:
            break

        nm = (d.get("name") or {}).get("default")
        if not nm:
            continue
        loc = d.get("location")
        if not (isinstance(loc, dict) and loc.get("type") == "Point" and
                isinstance(loc.get("coordinates"), list) and len(loc["coordinates"]) == 2):
            continue
        lon, lat = float(loc["coordinates"][0]), float(loc["coordinates"][1])

        # chiave dedup
        if d.get("wikidata_qid"):
            q = {"wikidata_qid": d["wikidata_qid"]}
        elif (d.get("wikipedia") or {}).get("it"):
            q = {"wikipedia.it": d["wikipedia"]["it"]}
        else:
            found = pois.find_one({
                "name.it": nm,
                "location": {"$near": {"$geometry": {"type":"Point","coordinates":[lon,lat]}, "$maxDistance": 15}}
            }, {"_id":1}) or pois.find_one({
                "name.en": nm,
                "location": {"$near": {"$geometry": {"type":"Point","coordinates":[lon,lat]}, "$maxDistance": 15}}
            }, {"_id":1})
            q = {"_id": found["_id"]} if found else {"name.it": nm, "location": {"type":"Point","coordinates":[lon,lat]}}

        # campi richiesti + safe defaults
        name_obj = {"it": nm, "en": nm}
        langs = sorted(set((d.get("langs") or [])) | {"it","en"})

        update = {
            "name": name_obj,
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "langs": langs,
            "last_refresh_at": now,     # ✅ richiesto dal validator
            "updated_at": now,
            "source": "osm",            # facoltativo ma utile
            "status": "active",         # facoltativo
        }
        wkd = d.get("wikidata_qid")
        if wkd: update["wikidata_qid"] = wkd
        wiki = d.get("wikipedia") or {}
        wiki_clean = {k:v for k,v in wiki.items() if k and v}
        if wiki_clean: update["wikipedia"] = wiki_clean

        res = pois.update_one(
            q,
            {"$setOnInsert": {"created_at": now}, "$set": update},
            upsert=True
        )
        if res.upserted_id:
            inserted += 1
        elif res.modified_count:   # ✅ conta solo se qualcosa è davvero cambiato
            updated += 1
            
        

    return {"inserted": inserted, "updated": updated}


def simulate_upsert_stats(docs: list[dict], radius_match_m: int = 15) -> dict:
    """
    Non scrive nulla. Conta quanti sarebbero insert/update secondo le stesse regole di dedup.
    """
    will_insert = 0
    will_update = 0
    for d in docs:
        nm = (d.get("name") or {}).get("default")
        loc = d.get("location")
        if not nm or not (isinstance(loc, dict) and loc.get("type") == "Point" and isinstance(loc.get("coordinates"), list) and len(loc["coordinates"]) == 2):
            continue
        lon, lat = float(loc["coordinates"][0]), float(loc["coordinates"][1])

        if d.get("wikidata_qid"):
            q = {"wikidata_qid": d["wikidata_qid"]}
        elif (d.get("wikipedia") or {}).get("it"):
            q = {"wikipedia.it": d["wikipedia"]["it"]}
        else:
            found = pois.find_one({
                "name.en": nm,
                "location": {"$near": {"$geometry": {"type":"Point","coordinates":[lon,lat]}, "$maxDistance": radius_match_m}}
            }, {"_id":1})
            if found:
                q = {"_id": found["_id"]}
            else:
                # non esiste già → sarebbe un insert
                will_insert += 1
                continue

        exists = pois.count_documents(q, limit=1) > 0
        if exists:
            will_update += 1
        else:
            will_insert += 1

    return {"inserted": will_insert, "updated": will_update}