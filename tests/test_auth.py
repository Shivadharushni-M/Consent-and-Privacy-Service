import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
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


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _build_app():
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app


def test_missing_api_key_returns_401():
    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/users",
            json={"email": "missing@example.com", "region": RegionEnum.EU.value},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid_api_key"


def test_wrong_api_key_returns_401():
    app = _build_app()
    with TestClient(app, headers={"X-API-Key": "wrong-key"}) as client:
        response = client.post(
            "/users",
            json={"email": "wrong@example.com", "region": RegionEnum.EU.value},
        )
        assert response.status_code == 401


def test_correct_api_key_allows_access():
    app = _build_app()
    with TestClient(app, headers={"X-API-Key": settings.API_KEY}) as client:
        response = client.post(
            "/users",
            json={"email": "ok@example.com", "region": RegionEnum.EU.value},
        )
        assert response.status_code == 201
        assert response.json()["email"] == "ok@example.com"


def test_region_endpoint_remains_public():
    app = _build_app()
    with TestClient(app) as client:
        response = client.get("/region", headers={"X-Forwarded-For": "8.8.8.8"})
        assert response.status_code == 200
        assert response.json()["region"] == RegionEnum.US.value


