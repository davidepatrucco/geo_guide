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

# AWS Lambda handler
handler = Mangum(app)