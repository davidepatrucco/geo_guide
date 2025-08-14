from fastapi import APIRouter, Response
from prometheus_client import CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest, Counter

router = APIRouter(tags=["System"])

# metrica semplice (esempio)
REQS = Counter("geoguide_requests_total", "Totale richieste (sample)", ["endpoint"])

@router.get("/metrics")
def metrics():
    data = generate_latest()  # default registry
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)