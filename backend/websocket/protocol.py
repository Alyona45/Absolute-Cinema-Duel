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


def serialize_error(message: str) -> dict[str, Any]:
    return ErrorMessage(payload=ErrorPayload(message=message)).model_dump()


def serialize_pong() -> dict[str, Any]:
    return PongMessage().model_dump()
