from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["version"])


@router.get("/version")
def get_version():
    return {
        "version": "1.0.0",
        "schema_version": "1.0",
    }


@router.get("/health")
def health_check():
    """Health check endpoint for Render and monitoring."""
    from sqlalchemy import text
    from app.db.database import engine
    try:
        # Check database connectivity
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}, 503
