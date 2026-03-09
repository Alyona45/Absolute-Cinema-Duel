import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.routers.auth import router as auth_router
from backend.routers.user import router as user_router
from backend.routers.movie import router as movie_router
from backend.routers.game_session import router as game_session_router
from backend.routers.ws import router as ws_router, room_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Фоновая задача: периодическая очистка неактивных комнат."""
    async def _cleanup_loop():
        while True:
            await asyncio.sleep(60)
            room_manager.cleanup_dead_rooms()

    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="Absolute Cinema Duel", lifespan=lifespan)

# Регистрация роутеров
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(movie_router)
app.include_router(game_session_router)
app.include_router(ws_router)

