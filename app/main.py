from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
engine_options = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    # SQLite connections are used across FastAPI's sync worker threads locally.
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(settings.database_url, **engine_options)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report that the API process is running; does not check dependencies."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    """Check whether the API can reach its configured database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Keep internal connection details out of the response.
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ready", "database": "available"}
