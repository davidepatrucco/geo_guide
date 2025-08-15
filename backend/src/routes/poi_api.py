from fastapi import APIRouter
from bson import ObjectId
from ..infra.db import poi_docs

router = APIRouter()

@router.get("/debug/poi_docs/{poi_id}")
def debug_poi_docs(poi_id: str):
    """Ritorna i documenti in poi_docs per il POI indicato."""
    try:
        oid = ObjectId(poi_id)
    except Exception:
        return {"error": "Invalid poi_id"}
    docs = list(poi_docs.find({"poi_id": oid}, {"_id": 0}))
    return {"items": docs}