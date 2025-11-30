from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.jobs.retention import run_retention_cleanup
from app.routes import (
    admin,
    consent,
    decision,
    events,
    preferences,
    region,
    retention,
    subject_requests,
    users,
    vendor_consent,
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
    app.include_router(decision.router)
    app.include_router(events.router)
    app.include_router(subject_requests.router)
    app.include_router(retention.router)
    app.include_router(admin.router)
    app.include_router(vendor_consent.router)

    @app.on_event("startup")
    def _startup() -> None:
        _ensure_scheduler()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        _shutdown_scheduler()

    @app.get("/")
    def root():
        return {"message": "Consent & Privacy Preferences Service", "status": "running"}

    @app.get("/health")
    def health_check():
        return {"status": "healthy"}

    return app


app = create_app()
