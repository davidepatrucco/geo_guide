from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ASCENDING, GEOSPHERE
from ..infra.db import pois
from math import radians, cos, sin, asin, sqrt

def ensure_indexes():
    pois.create_index([("location", GEOSPHERE)], name="geo_location")
    pois.create_index([("wikidata_qid", ASCENDING)], name="uq_wikidata_qid", unique=True, sparse=True)
    pois.create_index([("langs", ASCENDING)], name="langs")

def _oid(x): return x if isinstance(x, ObjectId) else ObjectId(x)

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = radians(lat2-lat1); dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(a))

def get(poi_id): return pois.find_one({"_id": _oid(poi_id)})
def get_many(ids): return list(pois.find({"_id": {"$in": [_oid(i) for i in ids]}}))

def insert(doc):
    now = datetime.now(timezone.utc)
    doc.setdefault("created_at", now); doc.setdefault("updated_at", now)
    return pois.insert_one(doc).inserted_id

def update(poi_id, data):
    data["updated_at"] = datetime.now(timezone.utc)
    return pois.update_one({"_id": _oid(poi_id)}, {"$set": data}).modified_count

def delete(poi_id): return pois.delete_one({"_id": _oid(poi_id)}).deleted_count

def nearby(lat: float, lon: float, radius_m: int, lang: str, limit: int = 10):
    q = {
        "location": {
            "$near": {
                "$geometry": {"type":"Point","coordinates":[lon,lat]},
                "$maxDistance": radius_m
            }
        }
    }
    try:
        cur = pois.find(q, {"name":1,"location":1,"wikipedia":1}).limit(20)
        used_near = True
    except Exception:
        cur = pois.find({}, {"name":1,"location":1,"wikipedia":1}).limit(200)
        used_near = False
    items=[]
    for p in cur:
        coords = p["location"]["coordinates"]
        dist = _haversine(lat, lon, coords[1], coords[0])
        if used_near or dist <= radius_m:
            name = p.get("name",{}).get(lang) or next(iter(p.get("name",{}).values()), "")
            items.append({
                "poi_id": str(p["_id"]),
                "name": name,
                "distance_m": round(dist,2),
                "coords": coords,
                "wiki_title": (p.get("wikipedia") or {}).get(lang)
            })
    items.sort(key=lambda x: x["distance_m"])
    return items[:limit]