import asyncio
from types import SimpleNamespace

import pytest

from backend.actors import CurrentActor, runtime_user_id_for_actor
from backend.websocket.manager import ConnectionManager
from backend.websocket.models import Participant, RoomStatus
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
        lambda self, host_actor: SimpleNamespace(invite_code="ABC123"),
    )

    actor = CurrentActor(
        user_id=7,
        guest_id=None,
        display_name="user",
        email="user@example.com",
    )

    payload = service.create_room(actor=actor)

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
        "backend.websocket.service.get_participants_by_session",
        lambda db, session_id: [
            SimpleNamespace(
                user=SimpleNamespace(email="user@example.com"),
                user_id=7,
            )
        ],
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


def test_guest_join_db_backed_session_is_allowed(monkeypatch) -> None:
    service = WsRoomService(
        db=DummyDB(),
        room_manager=RoomManager(),
        connection_manager=ConnectionManager(),
    )
    actor = CurrentActor(
        user_id=None,
        guest_id="guest-1",
        display_name="guest",
        email=None,
    )
    participant = SimpleNamespace(
        id=11,
        user_id=None,
        guest_id="guest-1",
        display_name="guest",
        user=None,
    )

    monkeypatch.setattr(
        "backend.websocket.service.GameSessionService.join_by_invite_code",
        lambda self, room_id, actor: participant,
    )
    monkeypatch.setattr(
        WsRoomService,
        "ensure_runtime_room",
        lambda self, room_id: self.room_manager.create_room(
            host_username="host",
            is_guest=True,
            room_id=room_id,
            user_id="guest:host",
        ) or self.room_manager.get_room(room_id),
    )

    payload = service.join_room(room_id="ABC123", actor=actor)

    assert payload["username"] == "guest"
    assert payload["user_id"] == runtime_user_id_for_actor(actor)


def test_start_room_rolls_back_runtime_status_on_db_error(monkeypatch) -> None:
    room_manager = RoomManager()
    service = WsRoomService(
        db=DummyDB(),
        room_manager=room_manager,
        connection_manager=ConnectionManager(),
    )

    room_manager.create_room(
        host_username="host",
        is_guest=False,
        email="host@example.com",
        room_id="ABC123",
        user_id="7",
    )

    actor = CurrentActor(
        user_id=7,
        guest_id=None,
        display_name="host",
        email="host@example.com",
    )

    def _raise_start_error(self, invite_code, actor_obj):
        raise InvalidOperationError("db start failed")

    monkeypatch.setattr(
        "backend.websocket.service.GameSessionService.start_session_by_invite_code",
        _raise_start_error,
    )

    async def _run() -> None:
        with pytest.raises(InvalidOperationError, match="db start failed"):
            await service.start_room(room_id="ABC123", actor=actor)

    asyncio.run(_run())

    room = room_manager.get_room("ABC123")
    assert room is not None
    assert room.status == RoomStatus.WAITING
