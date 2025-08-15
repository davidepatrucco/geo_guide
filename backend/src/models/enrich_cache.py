from datetime import datetime, timezone
from pymongo import ASCENDING, errors
from ..infra.db import enrich_cache

TTL_SECONDS = 30  # evita enrich ripetuti per stessa cella/raggio

def ensure_indexes():
    enrich_cache.create_index([("key", ASCENDING)], name="uq_key", unique=True)
    try:
        enrich_cache.create_index([("created_at", ASCENDING)], name="ttl_created_at", expireAfterSeconds=TTL_SECONDS)
    except Exception:
        pass

def _bucket(lat: float, lon: float, radius_m: int) -> str:
    # cella ~55m: 0.0005° -> round a 4e-4 (circa)
    lat_b = round(lat, 4); lon_b = round(lon, 4)
    rad_b = int(round(radius_m/50.0)*50)  # a step di 50m
    return f"{lat_b},{lon_b},r{rad_b}"

def should_enrich(lat: float, lon: float, radius_m: int) -> bool:
    key = _bucket(lat, lon, radius_m)
    try:
        enrich_cache.insert_one({"key": key, "created_at": datetime.now(timezone.utc)})
        return True  # primo che arriva: ok
    except errors.DuplicateKeyError:
        return False  # già fatto da poco