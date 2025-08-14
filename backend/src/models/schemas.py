from pydantic import BaseModel, Field, HttpUrl, constr, conlist
from typing import Optional, List, Literal

Locale = constr(pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
Style = Literal["guide", "quick", "kids", "anecdotes"]

class Error(BaseModel):
    code: str
    message: str

class POISummary(BaseModel):
    poi_id: str
    name: str
    distance_m: float
    coords: conlist(float, min_length=2, max_length=2)
    wiki_title: Optional[str] = None

class POIDetail(BaseModel):
    _id: str
    name: dict
    location: dict
    langs: List[Locale]
    wikidata_qid: Optional[str] = None
    wikipedia: Optional[dict] = None
    photos: Optional[List[str]] = None
    last_refresh_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class SourceRef(BaseModel):
    name: str
    url: HttpUrl

class NarrationRequest(BaseModel):
    poi_id: str
    style: Style
    lang: Locale
    voice: Optional[str] = None

class NarrationResponse(BaseModel):
    poi_id: str
    style: Style
    lang: Locale
    text: str
    audio_url: Optional[HttpUrl] = None
    sources: List[SourceRef]
    confidence: float = Field(ge=0, le=1)

class ContribPostRequest(BaseModel):
    poi_id: str
    text: constr(min_length=1, max_length=4000)
    lang: Locale

class ContribItem(BaseModel):
    _id: str
    poi_id: str
    lang: Locale
    text: str
    status: Literal["pending","approved","rejected"]
    created_at: str
    updated_at: Optional[str] = None

class UsageLogEvent(BaseModel):
    event: Literal["app.open","auth.login","poi.nearby","poi.view","narration.request",
                   "narration.generated","audio.play","contrib.posted","contrib.moderated","error"]
    ts: str
    user_hash: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    poi_id: Optional[str] = None
    latlon_q50m: Optional[str] = None
    app_ver: Optional[str] = None
    platform: Optional[Literal["ios","android","web"]] = None
    network: Optional[Literal["wifi","cellular","offline","unknown"]] = None
    outcome: Optional[Literal["ok","fail","cancel","timeout"]] = None
    error_code: Optional[str] = None
    latency_ms: Optional[int] = None
    size_bytes: Optional[int] = None
    extra: Optional[dict] = None

class AuthTokens(BaseModel):
    access_token: str
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = "Bearer"