from fastapi import FastAPI

from backend.routers.auth import router as auth_router
from backend.routers.user import router as user_router
from backend.routers.movie import router as movie_router
from backend.routers.game_session import router as game_session_router

app = FastAPI(title="Absolute Cinema Duel")

# Регистрация роутеров
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(movie_router)
app.include_router(game_session_router)

