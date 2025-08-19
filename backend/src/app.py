from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# importa i router dai controller
from .controllers.health_controller import router as health_router
from .controllers.auth_controller import router as auth_router
from .controllers.poi_controller import router as poi_router
from .controllers.narration_controller import router as narration_router
from .controllers.contrib_controller import router as contrib_router
from .controllers.config_controller import router as config_router
from .controllers.log_controller import router as log_router
from .controllers.metrics_controller import router as metrics_router
from .controllers import poi_docs_controller

# ====== DEBUG POI_DOCS ROUTE ======
from fastapi import APIRouter
from bson import ObjectId
from .infra.db import poi_docs

debug_router = APIRouter()

@debug_router.get("/debug/poi_docs/{poi_id}")
async def debug_poi_docs(poi_id: str):
    oid = ObjectId(poi_id)
    docs = list(poi_docs.find({"poi_id": oid}, {"_id": 0}))
    return {"count": len(docs), "docs": docs}
# ==================================

import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("services.narration_service").setLevel(logging.DEBUG)
logging.getLogger("controllers.poi_controller").setLevel(logging.DEBUG)
logging.getLogger("httpcore.http11").disabled = True
logging.getLogger("httpcore.connection").disabled = True
logging.getLogger("httpcore").disabled = True
logging.getLogger("httpx").disabled = True
logging.getLogger("pymongo").disabled = True
logging.getLogger("pymongo.serverSelection").disabled = True
logging.getLogger("pymongo.command").disabled = True

app = FastAPI(title="GeoGuide API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False
)

@app.middleware("http")
async def security_headers(req: Request, call_next):
    resp = await call_next(req)
    resp.headers["Content-Security-Policy"] = "default-src 'none'; connect-src 'self' https:; img-src 'self' https: data:;"
    resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp

# mount routers con prefix /v1
app.include_router(health_router,    prefix="/v1")
app.include_router(auth_router,      prefix="/v1")
app.include_router(poi_router,       prefix="/v1")
app.include_router(narration_router, prefix="/v1")
app.include_router(contrib_router,   prefix="/v1")
app.include_router(config_router,    prefix="/v1")
app.include_router(log_router,       prefix="/v1")
app.include_router(metrics_router,   prefix="/v1")
app.include_router(debug_router,     prefix="/v1")  # <== aggiunto qui
app.include_router(poi_docs_controller.router, prefix="/v1")
handler = Mangum(app)