from dataclasses import dataclass
import uuid

from backend.models import SessionParticipant

GUEST_TOKEN_COOKIE = "guest_token"
GUEST_RUNTIME_PREFIX = "guest:"


def generate_guest_id() -> str:
    return uuid.uuid4().hex


def generate_guest_name() -> str:
    return f"Гость_{uuid.uuid4().hex[:6]}"


@dataclass(frozen=True)
class CurrentActor:
    user_id: int | None
    guest_id: str | None
    display_name: str
    email: str | None = None

    @property
    def is_guest(self) -> bool:
        return self.user_id is None


def runtime_user_id_for_actor(actor: CurrentActor) -> str:
    if actor.user_id is not None:
        return str(actor.user_id)
    if actor.guest_id is None:
        raise ValueError("Guest actor requires guest_id")
    return f"{GUEST_RUNTIME_PREFIX}{actor.guest_id}"


def runtime_user_id_for_participant(participant: SessionParticipant) -> str:
    if participant.user_id is not None:
        return str(participant.user_id)
    if participant.guest_id is None:
        raise ValueError("Guest participant requires guest_id")
    return f"{GUEST_RUNTIME_PREFIX}{participant.guest_id}"


def guest_id_from_runtime_user_id(user_id: str) -> str | None:
    if not user_id.startswith(GUEST_RUNTIME_PREFIX):
        return None
    return user_id[len(GUEST_RUNTIME_PREFIX):] or None
