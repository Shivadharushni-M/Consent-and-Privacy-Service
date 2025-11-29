from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import consent, preferences, region, users
from app.config import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title="Consent & Privacy Preferences Service",
        version="1.0.0",
        description="Backend service for managing user consent and privacy preferences",
        debug=settings.DEBUG
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(users.router)
    app.include_router(consent.router)
    app.include_router(preferences.router)
    app.include_router(region.router)
    
    @app.get("/")
    def root():
        return {"message": "Consent & Privacy Preferences Service", "status": "running"}
    
    @app.get("/health")
    def health_check():
        return {"status": "healthy"}
    
    return app

app = create_app()
