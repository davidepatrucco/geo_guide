import os
import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.infra.db import get_db, pois

@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    os.environ["STAGE"] = "local"
    os.environ["MONGO_URI"] = "mongodb://localhost:27017"
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def clean_pois():
    db = get_db()
    db.pois.delete_many({})
    yield
    db.pois.delete_many({})