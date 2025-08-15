from __future__ import annotations
import os, time
from pathlib import Path
from typing import Optional, Literal, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

# --- percorsi .env (root progetto) ---
# file attuale: backend/src/infra/settings.py -> root = parents[3]
ROOT_DIR = Path(__file__).resolve().parents[3]
DOTENV_MAIN = ROOT_DIR / ".env"

# STAGE preliminare da env (default: local)
STAGE = os.getenv("STAGE", "local")
DOTENV_STAGE = ROOT_DIR / f".env.{STAGE}"

# carica prima .env (root), poi .env.<STAGE> (root) con override
load_dotenv(DOTENV_MAIN, override=False)
if DOTENV_STAGE.exists():
    load_dotenv(DOTENV_STAGE, override=True)

class Settings(BaseSettings):
    ENV: Literal["local","staging","prod"] = Field(default=STAGE)
    STAGE: Literal["local","staging","prod"] = Field(default=STAGE)
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME_BASE: str = "geo_guide"
    DB_NAME: Optional[str] = None

    # OIDC (per /auth)
    OIDC_ISS: Optional[str] = None              # es: https://auth.example.com/realms/xyz
    OIDC_CLIENT_ID: Optional[str] = None
    OIDC_REDIRECT_URI: Optional[str] = None     # es: https://app.example.com/callback
    OIDC_PROVIDER: Optional[str] = "keycloak"   # libero
    OIDC_TOKEN_URL: Optional[str] = None        # se non valorizzato -> {ISS}/protocol/openid-connect/token
    OIDC_AUTH_URL: Optional[str] = None         # se non valorizzato -> {ISS}/protocol/openid-connect/auth

    # Limiti
    POI_DEFAULT_RADIUS_M: int = 50
    NARRATION_MAX_CHARS: int = 1200

    # app_config refresh
    APP_CONFIG_CACHE_SECS: int = 60

    model_config = SettingsConfigDict(env_file=None, extra="allow")

_settings: Settings | None = None
_cfg_cache: Dict[str, Any] | None = None
_cfg_exp: float = 0.0
_mongo_client: MongoClient | None = None

def _db_name(s):
    """Nome DB in base all'origine"""
    if s.MONGO_URI.startswith("mongodb+srv://"):
        # Atlas → usa DB base senza suffisso
        return s.DB_NAME_BASE
    return f"{s.DB_NAME_BASE}_{s.STAGE}"


from pymongo import MongoClient

_mongo_client = None

def get_db():
    """Crea client Mongo con CA bundle per connessione sicura"""
    s = get_settings()
    global _mongo_client
    if _mongo_client is None:
        kwargs = {
            "serverSelectionTimeoutMS": 8000,
            "tlsCAFile": certifi.where()  # 🔹 Forza certificati validi sempre
        }
        _mongo_client = MongoClient(s.MONGO_URI, **kwargs)
    return _mongo_client[_db_name(s)]

def _load_app_config(s: Settings) -> Dict[str, Any]:
    global _cfg_cache, _cfg_exp
    now = time.time()
    if _cfg_cache and now < _cfg_exp:
        return _cfg_cache
    doc = get_db()["app_config"].find_one({}, sort=[("version",-1)]) or {}
    flags  = doc.get("flags", {}) or {}
    limits = doc.get("limits", {}) or {}
    llm    = doc.get("llm", {}) or {}
    _cfg_cache = {"flags": flags, "limits": limits, "llm": llm}
    _cfg_exp   = now + get_settings().APP_CONFIG_CACHE_SECS
    return _cfg_cache

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        cfg = _load_app_config(_settings)
        _settings.POI_DEFAULT_RADIUS_M = int(cfg.get("limits",{}).get("poi_radius_m", _settings.POI_DEFAULT_RADIUS_M))
        _settings.NARRATION_MAX_CHARS  = int(cfg.get("limits",{}).get("narration_max_chars", _settings.NARRATION_MAX_CHARS))
    return _settings