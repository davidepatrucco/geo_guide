from fastapi import APIRouter, HTTPException, Request
from jose import jwt, JWTError
import httpx, urllib.parse as urlparse
from ..infra.settings import get_settings
from ..models.schemas import AuthTokens
from ..models import user as user_model

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login")
def auth_login(payload: dict):
    s = get_settings()
    code_challenge = payload.get("code_challenge")
    redirect_uri = payload.get("redirect_uri") or s.OIDC_REDIRECT_URI
    if not (s.OIDC_ISS and s.OIDC_CLIENT_ID and code_challenge and redirect_uri):
        raise HTTPException(400, "OIDC: config/code_challenge/redirect_uri mancanti")
    auth_url = payload.get("auth_url") or s.OIDC_AUTH_URL or f"{s.OIDC_ISS}/protocol/openid-connect/auth"
    qs = {
        "client_id": s.OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return {"auth_url": f"{auth_url}?{urlparse.urlencode(qs)}"}

@router.post("/callback", response_model=AuthTokens)
async def auth_callback(payload: dict):
    s = get_settings()
    code = payload.get("code")
    code_verifier = payload.get("code_verifier")
    redirect_uri = payload.get("redirect_uri") or s.OIDC_REDIRECT_URI
    if not (s.OIDC_ISS and s.OIDC_CLIENT_ID and code and code_verifier and redirect_uri):
        raise HTTPException(400, "OIDC: parametri mancanti")

    token_url = s.OIDC_TOKEN_URL or f"{s.OIDC_ISS}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": s.OIDC_CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient(timeout=10) as hx:
        r = await hx.post(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"OIDC token error: {r.text}")
        tokens = r.json()

    # Decodifica soft (MVP). In prod valida via JWKS.
    try:
        claims = jwt.get_unverified_claims(tokens.get("id_token") or tokens.get("access_token"))
        user_model.upsert_from_claims(claims)  # salva/aggiorna utente
    except JWTError:
        pass

    return {
        "access_token": tokens.get("access_token"),
        "id_token": tokens.get("id_token"),
        "refresh_token": tokens.get("refresh_token"),
        "expires_in": tokens.get("expires_in"),
        "token_type": tokens.get("token_type", "Bearer"),
    }

@router.get("/me")
def me(authorization: str | None = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization[7:]
    try:
        claims = jwt.get_unverified_claims(token)  # TODO: JWKS verify in prod
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    # opzionale: sync utente ad ogni chiamata
    user_model.upsert_from_claims(claims)
    return {"sub": claims.get("sub"), "claims": claims}

@router.post("/logout", status_code=204)
def logout():
    return