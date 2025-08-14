from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from ..infra.settings import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/me")
def me(authorization: str | None = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization[7:]
    try:
        claims = jwt.get_unverified_claims(token)  # NOTE: MVP, senza verify
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"sub": claims.get("sub"), "claims": claims}

@router.post("/logout", status_code=204)
def logout():
    return