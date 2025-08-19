# controllers/poi_docs_controller.py
from fastapi import APIRouter
from bson import ObjectId
from ..infra.db import poi_docs

router = APIRouter()

@router.get("/poi/{poi_id}/docs")
async def get_poi_docs(poi_id: str, lang: str = None, limit: int = 10):
    try:
        poi_oid = ObjectId(poi_id)
    except:
        return {"detail": "Invalid POI ID"}

    query = {"poi_id": poi_oid}
    if lang:
        query["lang"] = lang

    docs = list(poi_docs.find(query).limit(limit))
    for d in docs:
        d["_id"] = str(d["_id"])
        d["poi_id"] = str(d["poi_id"])
    return docs