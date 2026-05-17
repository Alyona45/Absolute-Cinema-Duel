import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.auth import router as auth_router
from backend.routers.user import router as user_router
from backend.routers.movie import router as movie_router
from backend.routers.game_session import router as game_session_router
from backend.routers.ws import router as ws_router, room_manager
from backend.websocket.game_flappy import router as flappy_router
from backend.tournaments.router import router as tournament_router

logger = logging.getLogger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8001",
        "https://absolutecinemaduel.kotyan.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутеров
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(movie_router)
app.include_router(game_session_router)
app.include_router(ws_router)
app.include_router(flappy_router)
app.include_router(tournament_router)

# DEV: временно монтируем статическую папку `frontend/` под `/static`
# Это удобно для ручного тестирования клиента. Для production заменить
# на отдачу статики через CDN или отдельный веб-сервер (nginx).
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

