import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routers.auth import router as auth_router
from backend.routers.user import router as user_router
from backend.routers.movie import router as movie_router
from backend.routers.game_session import router as game_session_router
from backend.routers.ws import router as ws_router, room_manager

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
STORAGE_DIR = PROJECT_ROOT / "storage"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Фоновая задача: периодическая очистка неактивных комнат."""
    async def _cleanup_loop():
        while True:
            await asyncio.sleep(60)
            try:
                room_manager.cleanup_dead_rooms()
            except Exception as exc:
                logger.error("Ошибка в cleanup_dead_rooms: %s", exc, exc_info=True)

    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="Absolute Cinema Duel", lifespan=lifespan)

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="frontend-assets")

if STORAGE_DIR.exists():
    app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


@app.get("/", include_in_schema=False)
async def frontend_index() -> FileResponse:
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return FileResponse(
            path=(PROJECT_ROOT / "README.md"),
            media_type="text/plain",
            filename="README.md",
        )
    return FileResponse(index_file)

# Регистрация роутеров
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(movie_router)
app.include_router(game_session_router)
app.include_router(ws_router)

