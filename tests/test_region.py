import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import create_app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def test_region_detection_eu_mapping(client):
    response = client.get("/region", headers={"X-Forwarded-For": "2.16.0.1"})
    assert response.status_code == 200
    assert response.json()["region"] == "EU"


def test_region_detection_us_mapping(client):
    response = client.get("/region", headers={"X-Forwarded-For": "8.8.8.8"})
    assert response.status_code == 200
    assert response.json()["region"] == "US"


def test_region_detection_india_mapping(client):
    response = client.get("/region", headers={"X-Forwarded-For": "49.37.0.10"})
    assert response.status_code == 200
    assert response.json()["region"] == "INDIA"


def test_region_detection_non_listed_defaults_row(client):
    response = client.get("/region", headers={"X-Forwarded-For": "190.0.0.1"})
    assert response.status_code == 200
    assert response.json()["region"] == "ROW"


def test_region_detection_localhost_returns_row(client):
    response = client.get("/region", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 200
    assert response.json()["region"] == "ROW"


