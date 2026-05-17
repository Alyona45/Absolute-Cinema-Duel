from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.tournaments.router import router as tournament_router

logger = logging.getLogger(__name__)


def _ensure_demo_movies_seeded():
    """Ensure demo movies are loaded in database."""
    print("[STARTUP] Seeding demo movies on startup...")
    logger.info("[STARTUP] Seeding demo movies on startup...")
    
    try:
        from backend.tournaments.room_bus import RoomBus
        from backend.tournaments.service import TournamentService
        
        bus = RoomBus()
        service = TournamentService(bus=bus)
        result = service._seed_demo_movies_sync(target_count=16)
        print(f"[STARTUP] Movie seeding result: {result}")
        logger.info(f"[STARTUP] Movie seeding result: {result}")
    except Exception as e:
        print(f"[STARTUP] Error seeding movies: {e}")
        logger.error(f"[STARTUP] Error seeding movies: {e}", exc_info=True)


def create_app() -> FastAPI:
    app = FastAPI(title="Absolute Cinema Duel - MovieCO")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(tournament_router)

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.on_event("startup")
    async def startup_event():
        """Initialize demo movies on app startup."""
        print("[APP STARTUP] Triggering demo movie initialization...")
        _ensure_demo_movies_seeded()

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "MovieCO module ready", "ui": "/static/movieco/index.html"}

    return app


app = create_app()
