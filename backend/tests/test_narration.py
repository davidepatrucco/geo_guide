from bson import ObjectId
from datetime import datetime, timezone
from src.infra.db import pois, poi_docs, narrations_cache
from src.models.schemas import NarrationRequest

def seed_poi_and_docs():
    poi = {"name": {"en": "Test POI"}, "location": {"type":"Point","coordinates":[0,0]}, "langs": ["en"], "last_refresh_at": datetime.now(timezone.utc)}
    poi_id = pois.insert_one(poi).inserted_id
    poi_docs.insert_one({"poi_id": poi_id, "source":"wikipedia", "lang":"en", "content_text":"Test content", "created_at": datetime.now(timezone.utc)})
    return str(poi_id)

def test_narration_caching(client, clean_pois):
    pid = seed_poi_and_docs()
    rq = {"poi_id": pid, "lang":"en", "style":"guide"}
    r1 = client.post("/v1/narration", json=rq)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["text"]
    r2 = client.post("/v1/narration", json=rq)
    body2 = r2.json()
    assert body2["text"] == body1["text"]
    assert body2["confidence"] == body1["confidence"]