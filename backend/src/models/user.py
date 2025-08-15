from ..infra.db import users
from pymongo import ASCENDING

COLLECTION = "users"

def ensure_indexes():
    users.create_index([("sub", ASCENDING)], name="uq_sub", unique=True, sparse=True)   # OIDC subject
    users.create_index([("email", ASCENDING)], name="uq_email", unique=True, sparse=True)

def upsert_from_claims(claims: dict):
    """
    Inserisce o aggiorna un utente in base alle claims OIDC.
    """
    if not claims or "sub" not in claims:
        return None
    db = get_db()
    data = {
        "sub": claims["sub"],
        "email": claims.get("email"),
        "name": claims.get("name"),
        "given_name": claims.get("given_name"),
        "family_name": claims.get("family_name"),
        "updated_at": datetime.utcnow()
    }
    return db[COLLECTION].find_one_and_update(
        {"sub": claims["sub"]},
        {"$set": data, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )

def get_by_sub(sub: str):
    db = get_db()
    return db[COLLECTION].find_one({"sub": sub})

def list_users(limit: int = 50):
    db = get_db()
    return list(db[COLLECTION].find().limit(limit))