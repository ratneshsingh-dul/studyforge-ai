from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from app.main import app


def test_health_reports_running_api() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_hides_database_connection_details(monkeypatch) -> None:
    class UnavailableDatabase:
        def connect(self):
            raise SQLAlchemyError("private connection detail")

    monkeypatch.setattr("app.main.engine", UnavailableDatabase())
    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}


def test_readiness_succeeds_with_sqlite(monkeypatch) -> None:
    local_engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    monkeypatch.setattr("app.main.engine", local_engine)

    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "available"}
