from datetime import timedelta

from fastapi import Response

from backend.actors import GUEST_TOKEN_COOKIE
from backend.security import (
    create_guest_token,
    decode_guest_token,
    ensure_guest_actor,
)


def test_create_and_decode_guest_token_roundtrip() -> None:
    token = create_guest_token(
        guest_id="guest-123",
        display_name="Guest User",
        expires_delta=timedelta(minutes=5),
    )

    actor = decode_guest_token(token)

    assert actor is not None
    assert actor.user_id is None
    assert actor.guest_id == "guest-123"
    assert actor.display_name == "Guest User"
    assert actor.is_guest is True


def test_decode_guest_token_rejects_access_token_payload() -> None:
    token = create_guest_token(
        guest_id="guest-123",
        display_name="Guest User",
        expires_delta=timedelta(minutes=5),
    )
    tampered = token[::-1]

    actor = decode_guest_token(tampered)

    assert actor is None


def test_ensure_guest_actor_sets_signed_guest_token_cookie() -> None:
    response = Response()

    actor = ensure_guest_actor(
        response=response,
        current_actor=None,
        display_name="Guest Host",
    )

    assert actor.is_guest is True
    assert actor.display_name == "Guest Host"
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(header.startswith(f"{GUEST_TOKEN_COOKIE}=") for header in set_cookie_headers)
    assert any("HttpOnly" in header for header in set_cookie_headers)
