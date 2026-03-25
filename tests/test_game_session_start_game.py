import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.game_session_service import GameSessionService
from backend.actors import CurrentActor

client = TestClient(app)

# Моки для CurrentActor и сервисов (в реальных тестах используйте фикстуры и тестовую БД)
class DummyActor(CurrentActor):
    def __init__(self, user_id: int, display_name: str = "user"):
        super().__init__(user_id=user_id, guest_id=None, display_name=display_name, email=None)

def test_start_game_endpoint(monkeypatch):
    # Мокаем сервис и Depends
    session_id = 123
    actor = DummyActor(user_id=1)
    class DummyService:
        def start_game(self, sid, act):
            assert sid == session_id
            assert act.user_id == actor.user_id
            class DummySession:
                id = sid
                status = "PLAYING"
                host_user_id = None
                invite_code = "DUMMY"
                started_at = datetime.utcnow()
            return DummySession()
    import backend.routers.game_session as gs_mod
    # Use FastAPI dependency overrides so the Depends() in the router picks our mocks
    app.dependency_overrides[gs_mod.get_game_session_service] = lambda: DummyService()
    app.dependency_overrides[gs_mod.get_current_actor] = lambda: actor
    try:
        response = client.post(f"/sessions/{session_id}/start-game")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["status"] == "PLAYING"
