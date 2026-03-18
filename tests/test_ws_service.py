from types import SimpleNamespace

import pytest

from backend.websocket.manager import ConnectionManager
from backend.websocket.models import Participant
from backend.websocket.room import RoomManager
from backend.websocket.service import WsRoomService
from backend.services.errors import InvalidOperationError


class DummyDB:
    pass


def test_create_room_for_authenticated_user_uses_invite_code(monkeypatch) -> None:
    service = WsRoomService(
        db=DummyDB(),
        room_manager=RoomManager(),
        connection_manager=ConnectionManager(),
    )

    monkeypatch.setattr(
        "backend.websocket.service.GameSessionService.create_session",
        lambda self, host_user_id: SimpleNamespace(invite_code="ABC123"),
    )

    user = SimpleNamespace(id=7, email="user@example.com", username="user")

    payload = service.create_room(current_user=user, username=None)

    assert payload["room_id"] == "ABC123"
    assert payload["user_id"] == "7"


def test_validate_db_membership_requires_session_participant(monkeypatch) -> None:
    service = WsRoomService(
        db=DummyDB(),
        room_manager=RoomManager(),
        connection_manager=ConnectionManager(),
    )
    participant = Participant.authenticated(username="user", email="user@example.com")

    monkeypatch.setattr(
        "backend.websocket.service.get_game_session_by_invite_code",
        lambda db, invite_code: None,
    )

    assert service.validate_db_membership(room_id="ABC123", user_id="1", participant=participant) is False


def test_validate_db_membership_rejects_user_id_mismatch(monkeypatch) -> None:
    service = WsRoomService(
        db=DummyDB(),
        room_manager=RoomManager(),
        connection_manager=ConnectionManager(),
    )
    participant = Participant.authenticated(username="user", email="user@example.com")

    monkeypatch.setattr(
        "backend.websocket.service.get_game_session_by_invite_code",
        lambda db, invite_code: SimpleNamespace(id=42),
    )
    monkeypatch.setattr(
        "backend.websocket.service.get_user_by_email",
        lambda db, email: SimpleNamespace(id=7),
    )

    assert service.validate_db_membership(room_id="ABC123", user_id="8", participant=participant) is False


def test_get_room_rebuilds_runtime_room(monkeypatch) -> None:
    service = WsRoomService(
        db=DummyDB(),
        room_manager=RoomManager(),
        connection_manager=ConnectionManager(),
    )

    monkeypatch.setattr(
        WsRoomService,
        "_rebuild_runtime_room",
        lambda self, invite_code: SimpleNamespace(to_dict=lambda: {"status": "waiting"}),
    )

    room_payload = service.get_room("ABC123")

    assert room_payload == {"status": "waiting"}


def test_guest_join_is_rejected_for_db_backed_session(monkeypatch) -> None:
    service = WsRoomService(
        db=DummyDB(),
        room_manager=RoomManager(),
        connection_manager=ConnectionManager(),
    )

    monkeypatch.setattr(
        "backend.websocket.service.get_game_session_by_invite_code",
        lambda db, invite_code: SimpleNamespace(id=11),
    )

    with pytest.raises(InvalidOperationError):
        service.join_room(room_id="ABC123", current_user=None, username="guest")
