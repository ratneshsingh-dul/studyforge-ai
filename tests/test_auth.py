import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_register_login_and_logout_use_http_only_cookie(client: TestClient) -> None:
    registered = client.post(
        "/api/auth/register",
        json={"email": "Student@example.com", "password": "strong-password"},
    )
    assert registered.status_code == 201
    assert registered.json()["email"] == "student@example.com"
    assert "httponly" in registered.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").status_code == 200

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    logged_in = client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": "strong-password"},
    )
    assert logged_in.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_registration_rejects_duplicate_email_and_short_password(client: TestClient) -> None:
    payload = {"email": "student@example.com", "password": "strong-password"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409

    weak_password = {"email": "other@example.com", "password": "short"}
    assert client.post("/api/auth/register", json=weak_password).status_code == 422
