import re
from bson import ObjectId
from fastapi import HTTPException

_LOCALE_RE = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")

def ensure_locale(s: str) -> str:
    if not _LOCALE_RE.match(s):
        raise HTTPException(status_code=400, detail="Invalid locale")
    return s

def oid(oid_str: str) -> ObjectId:
    if not ObjectId.is_valid(oid_str):
        raise HTTPException(status_code=400, detail="Invalid ObjectId")
    return ObjectId(oid_str)