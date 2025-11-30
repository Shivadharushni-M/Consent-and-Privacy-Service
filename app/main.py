import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)
from app.jobs.retention import run_retention_cleanup
from app.routes import (
    admin,
    admin_catalog_v1,
    admin_policies_v1,
    admin_v1,
    consent,
    consents_v1,
    decision,
    decision_v1,
    events,
    preferences,
    region,
    retention,
    retention_v1,
    rights_v1,
    subject_requests,
    subjects_v1,
    users,
    vendor_consent,
    version,
)
# Import old v1 routes for backward compatibility
from app.routes.api.v1 import (
    subjects as v1_subjects,
    consents as v1_consents,
    decisions as v1_decisions,
    rights as v1_rights,
    admin as v1_admin,
    version as v1_version
)

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
    app = FastAPI(
        title="Consent & Privacy Preferences Service",
        version="1.0.0",
        description="Backend service for managing user consent and privacy preferences",
        debug=settings.DEBUG,
    )
    
    # Customize OpenAPI schema to add security scheme
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "Enter your API key (default: local-dev-key for local testing)"
            }
        }
        # Apply security to all endpoints
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
        """Log validation errors for debugging."""
        logger.error(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
        body = None
        if exc.body:
            try:
                body = exc.body.decode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                body = str(exc.body)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": body
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}")
        error_message = str(exc) if exc else "Unknown error"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": f"Internal server error: {error_message}",
                "type": type(exc).__name__
            },
        )

    # Legacy routes (kept for backward compatibility)
    app.include_router(users.router)
    app.include_router(consent.router)
    app.include_router(consent.preferences_router)
    app.include_router(preferences.router)
    app.include_router(region.router)
    app.include_router(decision.router)
    app.include_router(events.router)
    app.include_router(subject_requests.router)
    app.include_router(retention.router)
    app.include_router(admin.router)
    app.include_router(vendor_consent.router)
    
    # New v1 API routes
    app.include_router(subjects_v1.router)
    app.include_router(consents_v1.router)
    app.include_router(decision_v1.router)
    app.include_router(admin_policies_v1.router)
    app.include_router(admin_catalog_v1.router)
    app.include_router(admin_v1.router)
    app.include_router(rights_v1.router)
    app.include_router(rights_v1.admin_router)
    app.include_router(retention_v1.router)
    app.include_router(version.router)

    # Old v1 API routes (for backward compatibility)
    app.include_router(v1_subjects.router)
    app.include_router(v1_consents.router)
    app.include_router(v1_decisions.router)
    app.include_router(v1_rights.router)
    app.include_router(v1_admin.policies_router)
    app.include_router(v1_admin.catalog_router)
    app.include_router(v1_admin.admin_v1_router)
    app.include_router(v1_admin.rights_router)
    app.include_router(v1_admin.retention_router)
    app.include_router(v1_version.router)

    @app.on_event("startup")
    def _startup() -> None:
        _ensure_scheduler()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        _shutdown_scheduler()

    @app.get("/", tags=["default"])
    def root():
        return {"message": "Consent & Privacy Preferences Service", "status": "running"}

    @app.get("/health", tags=["default"])
    def health_check():
        """Health check endpoint (also available at /api/v1/health)."""
        from sqlalchemy import text
        from app.db.database import engine
        try:
            # Check database connectivity
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "database": "disconnected", "error": str(e)}, 503

    return app


app = create_app()
