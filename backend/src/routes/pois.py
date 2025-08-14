from fastapi import APIRouter, HTTPException, Body
from math import radians, cos, sin, asin, sqrt
from bson import ObjectId
from ..infra.db import pois
from ..infra.settings import settings
from ..models.schemas import POISummary
from ..utils.validators import ensure_locale

router = APIRouter(prefix="/poi", tags=["POI"])

def _haversine(lat1, lon1, lat2, lon2):
    # distanza in metri
    R = 6371000.0
    dlat = radians(lat2-lat1); dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(a))

@router.post("/nearby")
def nearby(payload: dict = Body(...)) -> dict:
    try:
        lat = float(payload["lat"]); lon = float(payload["lon"])
        radius = int(payload.get("radius_m", settings.POI_DEFAULT_RADIUS_M))
        lang = ensure_locale(payload.get("lang","en"))
    except Exception:
        raise HTTPException(status_code=400, detail="Bad request")
    # Usa $near se indice esiste; fallback bounding box + filtro
    q = {
        "location": {
            "$near": {
                "$geometry": {"type":"Point","coordinates":[lon,lat]},
                "$maxDistance": radius
            }
        }
    }
    try:
        cur = pois.find(q, {"name":1,"location":1,"wikipedia":1}).limit(20)
    except Exception:
        # fallback: scan locale (meno efficiente)
        cur = pois.find({}, {"name":1,"location":1,"wikipedia":1}).limit(200)
    items = []
    for p in cur:
        coords = p["location"]["coordinates"]
        dist = _haversine(lat, lon, coords[1], coords[0])
        if dist <= radius or "$near" not in q:
            name = p.get("name",{}).get(lang) or next(iter(p.get("name",{}).values()), "")
            items.append({
                "poi_id": str(p["_id"]),
                "name": name,
                "distance_m": round(dist,2),
                "coords": coords,
                "wiki_title": (p.get("wikipedia") or {}).get(lang)
            })
    items.sort(key=lambda x: x["distance_m"])
    return {"items": items[:10]}