from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    consent,
    users,
    region,
    decision,
    events,
    subject_requests,
    retention,
    admin,
    vendor_consent
)
from app.routes.api.v1 import (
    subjects as v1_subjects,
    consents as v1_consents,
    decisions as v1_decisions,
    rights as v1_rights,
    admin as v1_admin,
    version as v1_version
)
from app.config import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title="Consent & Privacy Preferences Service",
        version="1.0.0",
        description="Backend service for managing user consent and privacy preferences",
        debug=settings.DEBUG
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
    
    # Register all routers
    app.include_router(consent.router)
    app.include_router(consent.preferences_router)
    app.include_router(users.router)
    app.include_router(region.router)
    app.include_router(decision.router)
    app.include_router(events.router)
    app.include_router(subject_requests.router)
    app.include_router(retention.router)
    app.include_router(admin.router)
    app.include_router(vendor_consent.router)
    
    # API v1 routers
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
    
    @app.get("/", tags=["default"])
    def root():
        return {"message": "Consent & Privacy Preferences Service", "status": "running"}
    
    @app.get("/health", tags=["default"])
    def health_check():
        return {"status": "healthy"}
    
    return app

app = create_app()
