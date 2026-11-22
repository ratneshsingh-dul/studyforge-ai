from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import engine, initialize_database
from app.auth import router as auth_router
from app.documents import router as documents_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", on_startup=[initialize_database])
app.include_router(auth_router)
app.include_router(documents_router)


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
