from fastapi import FastAPI

from backend.routers.auth import router as auth_router
from backend.routers.user import router as user_router

app = FastAPI(title="Absolute Cinema Duel")

# Register routers
app.include_router(auth_router)
app.include_router(user_router)
