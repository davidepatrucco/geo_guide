from src.infra.db import pois
from bson import ObjectId

def test_nearby_empty(client, clean_pois):
    r = client.post("/v1/poi/nearby", json={"lat":0,"lon":0})
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
    assert r.json().get("items") == []

def test_get_poi_not_found(client):
    r = client.get(f"/v1/poi/{ObjectId()}")
    assert r.status_code == 404