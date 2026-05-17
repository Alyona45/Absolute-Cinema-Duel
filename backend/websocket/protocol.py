from typing import Any, Literal

from pydantic import BaseModel


class PingMessage(BaseModel):
    type: Literal["PING"]


class PongMessage(BaseModel):
    type: Literal["PONG"] = "PONG"


class RoomStatePayload(BaseModel):
    host_user_id: str
    participants: dict[str, dict[str, Any]]
    status: str
    # Optional — only populated once the host has picked a mini-game
    # on the /game-select screen. Late-joining clients read this on
    # WS connect to avoid being stuck on the "Ожидание хоста" state
    # after the host already advanced.
    selected_game: str | None = None


class RoomStateMessage(BaseModel):
    type: Literal["ROOM_STATE"] = "ROOM_STATE"
    payload: RoomStatePayload


class PlayerJoinedPayload(BaseModel):
    user_id: str
    username: str
    is_guest: bool


class PlayerJoinedMessage(BaseModel):
    type: Literal["PLAYER_JOINED"] = "PLAYER_JOINED"
    payload: PlayerJoinedPayload


class PlayerDisconnectedPayload(BaseModel):
    user_id: str


class PlayerDisconnectedMessage(BaseModel):
    type: Literal["PLAYER_DISCONNECTED"] = "PLAYER_DISCONNECTED"
    payload: PlayerDisconnectedPayload


class GameStartedPayload(BaseModel):
    room_id: str


class GameStartedMessage(BaseModel):
    type: Literal["GAME_STARTED"] = "GAME_STARTED"
    payload: GameStartedPayload


# ── Host's game choice is propagated to all participants over WS. All
# participants sit on `/session/{code}/game-select` after `GAME_STARTED`
# and need to move to the matching screen (`flappy` or the movie-picker
# that precedes `movieco`) once the host decides.
class GameSelectedPayload(BaseModel):
    room_id: str
    game_type: Literal["flappy", "movieco"]


class GameSelectedMessage(BaseModel):
    type: Literal["GAME_SELECTED"] = "GAME_SELECTED"
    payload: GameSelectedPayload


# ── Bug 3 fix: lobby/game sync events ───────────────────────────────
# When one participant mutates the session state (proposes a movie,
# removes a movie, or selects their own movie), every other connected
# participant must see the change through the WebSocket without having
# to act or reload. The payload includes the session_id plus whatever
# ids the client needs to update its local caches.


class MovieAddedPayload(BaseModel):
    session_id: int
    session_movie_id: int
    movie_id: int
    proposed_by_participant_id: int


class MovieAddedMessage(BaseModel):
    type: Literal["MOVIE_ADDED"] = "MOVIE_ADDED"
    payload: MovieAddedPayload


class MovieRemovedPayload(BaseModel):
    session_id: int
    session_movie_id: int


class MovieRemovedMessage(BaseModel):
    type: Literal["MOVIE_REMOVED"] = "MOVIE_REMOVED"
    payload: MovieRemovedPayload


class MovieSelectedPayload(BaseModel):
    session_id: int
    participant_id: int
    session_movie_id: int


class MovieSelectedMessage(BaseModel):
    type: Literal["MOVIE_SELECTED"] = "MOVIE_SELECTED"
    payload: MovieSelectedPayload


class ErrorPayload(BaseModel):
    message: str


class ErrorMessage(BaseModel):
    type: Literal["ERROR"] = "ERROR"
    payload: ErrorPayload


def serialize_room_state(room_data: dict[str, Any]) -> dict[str, Any]:
    return RoomStateMessage(
        payload=RoomStatePayload.model_validate(room_data),
    ).model_dump()


def serialize_player_joined(user_id: str, username: str, is_guest: bool) -> dict[str, Any]:
    return PlayerJoinedMessage(
        payload=PlayerJoinedPayload(user_id=user_id, username=username, is_guest=is_guest),
    ).model_dump()


def serialize_player_disconnected(user_id: str) -> dict[str, Any]:
    return PlayerDisconnectedMessage(
        payload=PlayerDisconnectedPayload(user_id=user_id),
    ).model_dump()


def serialize_game_started(room_id: str) -> dict[str, Any]:
    return GameStartedMessage(payload=GameStartedPayload(room_id=room_id)).model_dump()


def serialize_game_selected(room_id: str, game_type: str) -> dict[str, Any]:
    return GameSelectedMessage(
        payload=GameSelectedPayload(room_id=room_id, game_type=game_type),
    ).model_dump()


def serialize_movie_added(
    *,
    session_id: int,
    session_movie_id: int,
    movie_id: int,
    proposed_by_participant_id: int,
) -> dict[str, Any]:
    return MovieAddedMessage(
        payload=MovieAddedPayload(
            session_id=session_id,
            session_movie_id=session_movie_id,
            movie_id=movie_id,
            proposed_by_participant_id=proposed_by_participant_id,
        ),
    ).model_dump()


def serialize_movie_removed(*, session_id: int, session_movie_id: int) -> dict[str, Any]:
    return MovieRemovedMessage(
        payload=MovieRemovedPayload(
            session_id=session_id,
            session_movie_id=session_movie_id,
        ),
    ).model_dump()


def serialize_movie_selected(
    *,
    session_id: int,
    participant_id: int,
    session_movie_id: int,
) -> dict[str, Any]:
    return MovieSelectedMessage(
        payload=MovieSelectedPayload(
            session_id=session_id,
            participant_id=participant_id,
            session_movie_id=session_movie_id,
        ),
    ).model_dump()


def serialize_error(message: str) -> dict[str, Any]:
    return ErrorMessage(payload=ErrorPayload(message=message)).model_dump()


def serialize_pong() -> dict[str, Any]:
    return PongMessage().model_dump()
