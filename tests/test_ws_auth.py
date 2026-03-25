from backend.websocket.auth import validate_ws_participant_token
from backend.websocket.models import Participant


def test_guest_does_not_require_token() -> None:
    participant = Participant.guest("guest")

    error = validate_ws_participant_token(participant, token=None)

    assert error is None


def test_authenticated_requires_token() -> None:
    participant = Participant.authenticated("user", email="user@example.com")

    error = validate_ws_participant_token(participant, token=None)

    assert error == "Невалидный или отсутствующий токен"


def test_authenticated_token_mismatch(monkeypatch) -> None:
    participant = Participant.authenticated("user", email="owner@example.com")

    monkeypatch.setattr(
        "backend.websocket.auth.authenticate_ws_token",
        lambda token: "other@example.com",
    )

    error = validate_ws_participant_token(participant, token="jwt")

    assert error == "Токен не соответствует участнику комнаты"


def test_authenticated_token_match(monkeypatch) -> None:
    participant = Participant.authenticated("user", email="owner@example.com")

    monkeypatch.setattr(
        "backend.websocket.auth.authenticate_ws_token",
        lambda token: "owner@example.com",
    )

    error = validate_ws_participant_token(participant, token="jwt")

    assert error is None
