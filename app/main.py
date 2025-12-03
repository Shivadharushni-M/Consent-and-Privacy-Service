import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.jobs.retention import run_retention_cleanup
from app.routes import admin, admin_policies_v1, consent, decision, preferences, region, retention, subject_requests, users

logger = logging.getLogger(__name__)
_scheduler: Optional[BackgroundScheduler] = None


def _ensure_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_retention_cleanup,
        CronTrigger(hour=2, minute=0),
        id="retention-cleanup",
        replace_existing=True,
    )
    _scheduler.start()


def _shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Consent & Privacy Preferences Service",
        version="1.0.0",
        description="Backend service for managing user consent and privacy preferences",
        debug=settings.DEBUG,
    )
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi
        openapi_schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
        openapi_schema["components"]["securitySchemes"] = {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key", "description": "Enter your API key (default: local-dev-key for local testing)"}}
        for path in openapi_schema["paths"].values():
            for method in path.values():
                if isinstance(method, dict) and "security" not in method:
                    method["security"] = [{"ApiKeyAuth": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    app.openapi = custom_openapi

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        json_errors = [e for e in errors if e.get("type") == "json_invalid"]
        if json_errors:
            error = json_errors[0]
            ctx_error = error.get("ctx", {}).get("error", "")
            detail = ("Invalid JSON format. Common issues:\n- Missing comma between properties\n- Trailing comma (not allowed in JSON)\n- Missing quotes around property names or string values" if "Expecting ',' delimiter" in ctx_error or "Expecting property name" in ctx_error else f"JSON parsing error: {error.get('msg', 'Invalid JSON')}")
            logger.error(f"JSON parsing error on {request.method} {request.url.path}: {detail}")
            return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail, "error_type": "json_invalid"})
        value_errors = [e for e in errors if e.get("type") == "value_error"]
        if value_errors:
            error = value_errors[0]
            error_msg = str(error.get("msg", ""))
            detail = ("Cannot specify both 'expires_at' and 'expires_in_days'. Provide only one: 'expires_at' (datetime) or 'expires_in_days' (integer)." if "expires_at" in error_msg.lower() and "expires_in_days" in error_msg.lower() else error.get("ctx", {}).get("error", error_msg))
            logger.error(f"Validation error on {request.method} {request.url.path}: {detail}")
            return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail, "error_type": "validation_error"})
        logger.error(f"Validation error on {request.method} {request.url.path}: {errors}")
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": errors})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        error_message = str(exc) if exc else "Invalid value"
        logger.warning(f"ValueError on {request.method} {request.url.path}: {error_message}")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": error_message})

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        error_message = str(exc) if exc else "Unknown error"
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {error_message}", exc_info=exc)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"Internal server error: {error_message}"})

    app.include_router(users.router)
    app.include_router(consent.router)
    app.include_router(preferences.router)
    app.include_router(region.router)
    app.include_router(decision.router)
    app.include_router(subject_requests.router)
    app.include_router(admin.router)
    app.include_router(retention.router)
    app.include_router(admin_policies_v1.router)

    @app.on_event("startup")
    def _startup() -> None:
        _ensure_scheduler()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        _shutdown_scheduler()

    @app.get("/health", tags=["system"])
    def health_check():
        from sqlalchemy import text
        from app.db.database import engine
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "disconnected", "error": str(e)})

    return app


app = create_app()
