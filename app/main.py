import json
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
    decision,
    events,
    preferences,
    region,
    retention,
    retention_v1,
    subject_requests,
    users,
    vendor_consent,
    version,
)
# Also import v1 routes from api.v1 for backward compatibility
from app.routes.api.v1 import (
    admin as v1_admin,
    version as v1_version
)

_scheduler: Optional[BackgroundScheduler] = None


def _make_json_serializable(obj):
    """Recursively convert objects to JSON-serializable format."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    # For any other type, convert to string
    return str(obj)


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
        # Get errors and ensure they're JSON-serializable
        errors = exc.errors()
        # Clean up errors to ensure all values are JSON-serializable
        serializable_errors = _make_json_serializable(errors)
        
        # Check for JSON parsing errors and provide helpful messages
        json_errors = [e for e in errors if e.get("type") == "json_invalid"]
        if json_errors:
            json_error = json_errors[0]
            error_msg = json_error.get("msg", "JSON decode error")
            ctx_error = json_error.get("ctx", {}).get("error", "")
            
            # Provide helpful message for common JSON errors
            if "Expecting ',' delimiter" in ctx_error or "Expecting property name" in ctx_error:
                helpful_msg = (
                    "Invalid JSON format. Common issues:\n"
                    "- Missing comma between properties (e.g., use: {\"email\": \"test@example.com\", \"region\": \"EU\"})\n"
                    "- Trailing comma (not allowed in JSON)\n"
                    "- Missing quotes around property names or string values"
                )
            else:
                helpful_msg = f"JSON parsing error: {error_msg}. {ctx_error if ctx_error else ''}"
            
            logger.error(f"JSON parsing error on {request.method} {request.url.path}: {helpful_msg}")
            body = None
            if exc.body:
                try:
                    body = exc.body.decode('utf-8') if isinstance(exc.body, bytes) else str(exc.body)
                except (UnicodeDecodeError, AttributeError):
                    body = str(exc.body)
            
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": helpful_msg,
                    "error_type": "json_invalid",
                    "original_error": error_msg,
                    "body": body
                },
            )
        
        # Check for value_error type (from model_validator) and provide helpful messages
        value_errors = [e for e in errors if e.get("type") == "value_error"]
        if value_errors:
            value_error = value_errors[0]
            error_msg = value_error.get("msg", "")
            ctx_error = value_error.get("ctx", {}).get("error", "")
            
            # Provide helpful message for common validation errors
            if "expires_at" in str(error_msg).lower() and "expires_in_days" in str(error_msg).lower():
                helpful_msg = (
                    "Validation Error: Cannot specify both 'expires_at' and 'expires_in_days'.\n\n"
                    "Please provide only ONE of the following:\n"
                    "• Use 'expires_at' with a specific date/time (e.g., \"2025-12-01T05:33:33.919Z\")\n"
                    "• Use 'expires_in_days' with a number (e.g., 1 for 1 day from now)\n\n"
                    "Example with expires_at:\n"
                    '  {"user_id": "...", "purpose": "analytics", "region": "EU", "expires_at": "2025-12-01T05:33:33.919Z"}\n\n'
                    "Example with expires_in_days:\n"
                    '  {"user_id": "...", "purpose": "analytics", "region": "EU", "expires_in_days": 1}'
                )
            else:
                helpful_msg = ctx_error if ctx_error else error_msg
            
            logger.error(f"Validation error on {request.method} {request.url.path}: {helpful_msg}")
            body = None
            if exc.body:
                try:
                    body = exc.body.decode('utf-8') if isinstance(exc.body, bytes) else str(exc.body)
                except (UnicodeDecodeError, AttributeError):
                    body = str(exc.body)
            
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": helpful_msg,
                    "error_type": "validation_error",
                    "original_errors": serializable_errors
                },
            )
        
        logger.error(f"Validation error on {request.method} {request.url.path}: {serializable_errors}")
        body = None
        if exc.body:
            try:
                body = exc.body.decode('utf-8') if isinstance(exc.body, bytes) else str(exc.body)
            except (UnicodeDecodeError, AttributeError):
                body = str(exc.body)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": serializable_errors,
                "body": body
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions and convert them to proper HTTP responses."""
        error_message = str(exc) if exc else "Invalid value"
        logger.warning(f"ValueError on {request.method} {request.url.path}: {error_message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": error_message
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        # Safely convert exception to string for logging
        exc_str = "Unknown error"
        try:
            if exc:
                exc_str = str(exc)
            logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc_str}", exc_info=exc)
        except Exception as log_exc:
            # If logging fails, just log the type
            logger.error(f"Unhandled exception on {request.method} {request.url.path} (type: {type(exc).__name__}, logging error: {type(log_exc).__name__})")
            exc_str = f"Error of type {type(exc).__name__}"
        
        # Ensure error_message is always a string, not an exception object
        error_message = "Unknown error"
        try:
            if exc:
                error_message = str(exc)
        except Exception:
            error_message = f"Error of type {type(exc).__name__}"
        
        # Ensure all content values are JSON-serializable strings
        error_type_name = "Exception"
        try:
            error_type_name = str(type(exc).__name__)
        except Exception:
            pass
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": f"Internal server error: {error_message}",
                "type": error_type_name
            },
        )

    # Legacy routes (kept for backward compatibility)
    app.include_router(users.router)
    app.include_router(consent.router)
    if hasattr(consent, 'preferences_router'):
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
    app.include_router(admin_policies_v1.router)
    app.include_router(admin_catalog_v1.router)
    app.include_router(admin_v1.router)
    app.include_router(retention_v1.router)
    app.include_router(version.router)
    
    # Also include old v1 routes for backward compatibility
    # Note: policies_router is excluded here because admin_policies_v1.router provides the proper implementation
    # Note: catalog_router is excluded here because admin_catalog_v1.router provides the proper implementation
    # if hasattr(v1_admin, 'policies_router'):
    #     app.include_router(v1_admin.policies_router)
    # if hasattr(v1_admin, 'catalog_router'):
    #     app.include_router(v1_admin.catalog_router)
    if hasattr(v1_admin, 'admin_v1_router'):
        app.include_router(v1_admin.admin_v1_router)
    # retention_router is commented out in v1_admin - use retention_v1.router instead
    # if hasattr(v1_admin, 'retention_router'):
    #     app.include_router(v1_admin.retention_router)
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
