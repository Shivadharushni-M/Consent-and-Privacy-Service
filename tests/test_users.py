import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import create_app
from app.models.consent import RegionEnum

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


def test_create_user_success(client):
    response = client.post(
        "/users",
        json={"email": "alice@example.com", "region": RegionEnum.EU.value},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["region"] == RegionEnum.EU.value
    assert "id" in data


def test_create_user_invalid_region(client):
    response = client.post("/users", json={"email": "bad@example.com", "region": "MARS"})
    assert response.status_code == 422


def test_get_user_success(client):
    created = client.post(
        "/users",
        json={"email": "bob@example.com", "region": RegionEnum.US.value},
    ).json()

    response = client.get(f"/users/{created['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["region"] == RegionEnum.US.value


def test_get_user_invalid_uuid(client):
    response = client.get("/users/not-a-uuid")
    assert response.status_code == 422


def test_get_user_not_found(client):
    response = client.get(f"/users/{uuid.uuid4()}")
    assert response.status_code == 404


def test_update_region_success(client):
    created = client.post(
        "/users",
        json={"email": "carol@example.com", "region": RegionEnum.AU.value},
    ).json()

    response = client.patch(
        f"/users/{created['id']}",
        json={"region": RegionEnum.CA.value},
    )
    assert response.status_code == 200
    assert response.json()["region"] == RegionEnum.CA.value


def test_update_region_invalid_region(client):
    created = client.post(
        "/users",
        json={"email": "dave@example.com", "region": RegionEnum.IN.value},
    ).json()

    response = client.patch(f"/users/{created['id']}", json={"region": "LUNAR"})
    assert response.status_code == 422


def test_duplicate_email_conflict(client):
    payload = {"email": "duplicate@example.com", "region": RegionEnum.EU.value}
    assert client.post("/users", json=payload).status_code == 201

    response = client.post("/users", json=payload)
    assert response.status_code == 409

