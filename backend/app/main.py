from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import filings, health, research


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FinSight API",
        version="0.1.0",
        description="Multi-agent financial research backend.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(filings.router, prefix="/filings", tags=["filings"])
    app.include_router(research.router, prefix="/research", tags=["research"])

    return app


app = create_app()
