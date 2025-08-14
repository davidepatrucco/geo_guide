from __future__ import annotations
import os, time
from pathlib import Path
from typing import Optional, Literal, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

# --- Caricamento .env robusto (path fisso alla cartella backend) ---
BASE_DIR = Path(__file__).resolve().parents[2]   # .../backend
DOTENV_MAIN = BASE_DIR / ".env"

STAGE = os.getenv("STAGE", "staging")
DOTENV_STAGE = BASE_DIR / f".env.{STAGE}"

# Carica prima .env, poi .env.<stage> con precedenza
load_dotenv(DOTENV_MAIN, override=False)
if DOTENV_STAGE.exists():
    load_dotenv(DOTENV_STAGE, override=True)

class Settings(BaseSettings):
    ENV: Literal["local","staging","prod"] = Field(default=STAGE)
    STAGE: Literal["local","staging","prod"] = Field(default=STAGE)
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME_BASE: str = "geo_guide"
    DB_NAME: Optional[str] = None
    POI_DEFAULT_RADIUS_M: int = 120
    NARRATION_MAX_CHARS: int = 1200
    APP_CONFIG_CACHE_SECS: int = 60
    model_config = SettingsConfigDict(env_file=None, extra="allow")

_settings: Settings | None = None
_cfg_cache: Dict[str, Any] | None = None
_cfg_exp: float = 0.0
_mongo_client: MongoClient | None = None

def _db_name(s: Settings) -> str:
    # Atlas (SRV): usa base senza suffisso
    if s.MONGO_URI.startswith("mongodb+srv://"):
        return s.DB_NAME_BASE
    # locale/altro: suffisso per stage
    return f"{s.DB_NAME_BASE}_{s.STAGE}"

def get_db():
    """Client Mongo con CA bundle (Atlas) e senza forzare connessione a import-time."""
    s = get_settings()
    global _mongo_client
    if _mongo_client is None:
        kwargs = {"serverSelectionTimeoutMS": 8000, "tlsCAFile": certifi.where()}
        _mongo_client = MongoClient(s.MONGO_URI, **kwargs)
        # log diagnostico minimale
        print(f"[settings] STAGE={s.STAGE} DB={_db_name(s)} URI={'srv' if s.MONGO_URI.startswith('mongodb+srv://') else 'local'}")
    return _mongo_client[_db_name(s)]

def _load_app_config(s: Settings) -> Dict[str, Any]:
    global _cfg_cache, _cfg_exp
    now = time.time()
    if _cfg_cache and now < _cfg_exp:
        return _cfg_cache
    try:
        doc = get_db()["app_config"].find_one({}, sort=[("version",-1)]) or {}
        flags  = doc.get("flags", {}) or {}
        limits = doc.get("limits", {}) or {}
        llm    = doc.get("llm", {}) or {}
    except Exception:
        flags, limits, llm = {}, {}, {}
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