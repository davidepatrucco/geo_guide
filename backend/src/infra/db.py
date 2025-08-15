from .settings import get_db
db = get_db()

pois             = db["pois"]
poi_docs         = db["poi_docs"]
narrations_cache = db["narrations_cache"]
user_contrib     = db["user_contrib"]
usage_logs       = db["usage_logs"]
users            = db["users"]
app_config       = db["app_config"] 
enrich_cache     = db["nearby_enrich_cache"]  # TTL cache anti-enrich ripetuto