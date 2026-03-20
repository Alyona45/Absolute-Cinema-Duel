from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import get_db
from backend.main import app
from backend.models import Base
from backend.routers.ws import conn_manager, room_manager


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "e2e_http_ws.sqlite3"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db: Session = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    room_manager.rooms.clear()
    conn_manager.connections.clear()
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan
    room_manager.rooms.clear()
    conn_manager.connections.clear()
    engine.dispose()


def _register_and_login(client: TestClient, email: str, username: str, password: str) -> dict[str, str]:
    register_response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text

    body = login_response.json()
    return {
        "access_token": body["access_token"],
        "auth_header": f"Bearer {body['access_token']}",
    }


def _create_room(client: TestClient, auth_header: str) -> tuple[str, str]:
    response = client.post(
        "/rooms",
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 201, response.text

    body = response.json()
    return body["room_id"], body["user_id"]


def _join_room(client: TestClient, room_id: str, auth_header: str) -> str:
    response = client.post(
        f"/rooms/{room_id}/join",
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 201, response.text
    return response.json()["user_id"]


def _get_session_id_by_invite_code(
    client: TestClient,
    auth_header: str,
    invite_code: str,
) -> int:
    response = client.get(
        "/sessions/my/list",
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 200, response.text

    sessions = response.json()
    for session in sessions:
        if session["invite_code"] == invite_code:
            return session["id"]

    raise AssertionError(f"Session with invite_code={invite_code} was not found")


def _select_participant_movie(
    client: TestClient,
    session_id: int,
    auth_header: str,
    movie_id: int,
) -> int:
    propose_response = client.post(
        f"/sessions/{session_id}/movies",
        params={"movie_id": movie_id},
        headers={"Authorization": auth_header},
    )
    assert propose_response.status_code == 201, propose_response.text
    session_movie_id = propose_response.json()["id"]

    select_response = client.post(
        f"/sessions/{session_id}/selection",
        json={"session_movie_id": session_movie_id},
        headers={"Authorization": auth_header},
    )
    assert select_response.status_code == 200, select_response.text
    assert select_response.json()["selected_session_movie_id"] == session_movie_id

    return session_movie_id


def _create_movie(
    client: TestClient,
    auth_header: str,
    kinopoisk_id: int,
    title: str,
) -> int:
    response = client.post(
        "/movies",
        headers={"Authorization": auth_header},
        json={
            "kinopoisk_id": kinopoisk_id,
            "title": title,
            "short_description": "test",
            "description": "test",
            "poster_url": "https://example.com/poster.jpg",
            "year": 2024,
            "runtime": 100,
            "rating": 8.1,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_e2e_host_create_and_receive_room_state(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host1@example.com",
        username="host1",
        password="Password123",
    )
    room_id, host_user_id = _create_room(client, host_auth["auth_header"])

    with client.websocket_connect(
        f"/ws/{room_id}/{host_user_id}?token={host_auth['access_token']}"
    ) as host_ws:
        room_state = host_ws.receive_json()

    assert room_state["type"] == "ROOM_STATE"
    assert room_state["payload"]["host_user_id"] == host_user_id
    assert host_user_id in room_state["payload"]["participants"]


def test_e2e_participant_join_and_host_gets_player_joined(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host2@example.com",
        username="host2",
        password="Password123",
    )
    participant_auth = _register_and_login(
        client,
        email="participant2@example.com",
        username="participant2",
        password="Password123",
    )

    room_id, host_user_id = _create_room(client, host_auth["auth_header"])
    participant_user_id = _join_room(client, room_id, participant_auth["auth_header"])

    with client.websocket_connect(
        f"/ws/{room_id}/{host_user_id}?token={host_auth['access_token']}"
    ) as host_ws:
        host_ws.receive_json()
        with client.websocket_connect(
            f"/ws/{room_id}/{participant_user_id}?token={participant_auth['access_token']}"
        ) as participant_ws:
            participant_ws.receive_json()
            joined_event = host_ws.receive_json()

    assert joined_event["type"] == "PLAYER_JOINED"
    assert joined_event["payload"]["user_id"] == participant_user_id


def test_e2e_start_session_broadcasts_game_started(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host3@example.com",
        username="host3",
        password="Password123",
    )
    participant_auth = _register_and_login(
        client,
        email="participant3@example.com",
        username="participant3",
        password="Password123",
    )

    room_id, host_user_id = _create_room(client, host_auth["auth_header"])
    participant_user_id = _join_room(client, room_id, participant_auth["auth_header"])
    session_id = _get_session_id_by_invite_code(client, host_auth["auth_header"], room_id)

    host_movie_id = _create_movie(
        client,
        host_auth["auth_header"],
        kinopoisk_id=70000021,
        title="Host Selected Movie",
    )
    participant_movie_id = _create_movie(
        client,
        participant_auth["auth_header"],
        kinopoisk_id=70000022,
        title="Participant Selected Movie",
    )

    _select_participant_movie(client, session_id, host_auth["auth_header"], host_movie_id)
    _select_participant_movie(
        client,
        session_id,
        participant_auth["auth_header"],
        participant_movie_id,
    )

    with client.websocket_connect(
        f"/ws/{room_id}/{host_user_id}?token={host_auth['access_token']}"
    ) as host_ws:
        host_ws.receive_json()
        with client.websocket_connect(
            f"/ws/{room_id}/{participant_user_id}?token={participant_auth['access_token']}"
        ) as participant_ws:
            participant_ws.receive_json()
            host_ws.receive_json()

            start_response = client.post(
                f"/rooms/{room_id}/start",
                headers={"Authorization": host_auth["auth_header"]},
            )

            host_started_event = host_ws.receive_json()
            participant_started_event = participant_ws.receive_json()

    assert start_response.status_code == 200, start_response.text
    assert host_started_event["type"] == "GAME_STARTED"
    assert participant_started_event["type"] == "GAME_STARTED"


def test_e2e_non_member_with_valid_jwt_is_denied(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host4@example.com",
        username="host4",
        password="Password123",
    )
    outsider_auth = _register_and_login(
        client,
        email="outsider4@example.com",
        username="outsider4",
        password="Password123",
    )

    room_id, _ = _create_room(client, host_auth["auth_header"])

    with client.websocket_connect(
        f"/ws/{room_id}/99999?token={outsider_auth['access_token']}"
    ) as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()

    assert exc_info.value.code == 4004


def test_e2e_jwt_user_id_mismatch_is_denied(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host5@example.com",
        username="host5",
        password="Password123",
    )
    participant_auth = _register_and_login(
        client,
        email="participant5@example.com",
        username="participant5",
        password="Password123",
    )

    room_id, _ = _create_room(client, host_auth["auth_header"])

    participant_user_id = _join_room(client, room_id, participant_auth["auth_header"])

    with client.websocket_connect(
        f"/ws/{room_id}/{participant_user_id}?token={host_auth['access_token']}"
    ) as ws:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()

    assert exc_info.value.code == 4001


def test_e2e_reconnect_restores_room_state_from_db(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host6@example.com",
        username="host6",
        password="Password123",
    )
    participant_auth = _register_and_login(
        client,
        email="participant6@example.com",
        username="participant6",
        password="Password123",
    )

    room_id, host_user_id = _create_room(client, host_auth["auth_header"])
    participant_user_id = _join_room(client, room_id, participant_auth["auth_header"])

    room_manager.rooms.clear()

    with client.websocket_connect(
        f"/ws/{room_id}/{host_user_id}?token={host_auth['access_token']}"
    ) as host_ws:
        room_state = host_ws.receive_json()

    assert room_state["type"] == "ROOM_STATE"
    assert participant_user_id in room_state["payload"]["participants"]


def test_e2e_pick_winner_by_participant_uses_selected_movie(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host7@example.com",
        username="host7",
        password="Password123",
    )
    participant_auth = _register_and_login(
        client,
        email="participant7@example.com",
        username="participant7",
        password="Password123",
    )

    room_id, _ = _create_room(client, host_auth["auth_header"])

    join_by_code_response = client.post(
        "/sessions/join-by-code",
        json={"invite_code": room_id},
        headers={"Authorization": participant_auth["auth_header"]},
    )
    assert join_by_code_response.status_code == 201, join_by_code_response.text
    session_participant = join_by_code_response.json()
    session_id = session_participant["session_id"]
    participant_id = session_participant["id"]

    movie_id = _create_movie(
        client,
        host_auth["auth_header"],
        kinopoisk_id=7000001,
        title="Winner Movie",
    )

    session_movie_id = _select_participant_movie(
        client,
        session_id,
        participant_auth["auth_header"],
        movie_id,
    )

    finalize_response = client.post(
        f"/sessions/{session_id}/winner/by-participant",
        json={"winner_participant_id": participant_id},
        headers={"Authorization": host_auth["auth_header"]},
    )

    assert finalize_response.status_code == 200, finalize_response.text
    assert finalize_response.json()["winner_session_movie_id"] == session_movie_id


def test_e2e_start_session_denied_when_not_all_selected(client: TestClient) -> None:
    host_auth = _register_and_login(
        client,
        email="host8@example.com",
        username="host8",
        password="Password123",
    )
    participant_auth = _register_and_login(
        client,
        email="participant8@example.com",
        username="participant8",
        password="Password123",
    )

    room_id, _ = _create_room(client, host_auth["auth_header"])
    _join_room(client, room_id, participant_auth["auth_header"])
    session_id = _get_session_id_by_invite_code(client, host_auth["auth_header"], room_id)

    host_movie_id = _create_movie(
        client,
        host_auth["auth_header"],
        kinopoisk_id=70000031,
        title="Host Only Selected",
    )
    _select_participant_movie(client, session_id, host_auth["auth_header"], host_movie_id)

    start_response = client.post(
        f"/rooms/{room_id}/start",
        headers={"Authorization": host_auth["auth_header"]},
    )

    assert start_response.status_code == 400, start_response.text
    assert "каждый участник" in start_response.json()["detail"]
