import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.security import get_current_user_optional
from backend.websocket.manager import ConnectionManager
from backend.websocket.auth import validate_ws_participant_token
from backend.websocket.protocol import (
    PingMessage,
    serialize_error,
    serialize_player_disconnected,
    serialize_player_joined,
    serialize_pong,
    serialize_room_state,
)
from backend.websocket.room import RoomManager
from backend.websocket.service import WsRoomService
from backend.services.errors import (
    AccessDeniedError,
    InvalidOperationError,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Синглтоны — живут пока работает сервер
conn_manager = ConnectionManager()
room_manager = RoomManager()


# ─────────────────── HTTP эндпоинты (комнаты) ──────────


class RoomBody(BaseModel):
    """Тело запроса для создания/присоединения к комнате."""
    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
        description="Имя гостя. Используется только если нет авторизации.",
    )


def get_ws_room_service(db: Session = Depends(get_db)) -> WsRoomService:
    return WsRoomService(db=db, room_manager=room_manager, connection_manager=conn_manager)


@router.post("/rooms", status_code=201)
def create_room(
    body: RoomBody | None = None,
    current_user: models.User | None = Depends(get_current_user_optional),
    service: WsRoomService = Depends(get_ws_room_service),
):
    return service.create_room(current_user=current_user, username=body.username if body else None)


@router.post("/rooms/{room_id}/join", status_code=201)
def join_room(
    room_id: str,
    body: RoomBody | None = None,
    current_user: models.User | None = Depends(get_current_user_optional),
    service: WsRoomService = Depends(get_ws_room_service),
):
    try:
        return service.join_room(
            room_id=room_id,
            current_user=current_user,
            username=body.username if body else None,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ─────────────────── Общие HTTP эндпоинты ─────────────────────


@router.post("/rooms/{room_id}/start")
async def start_room(
    room_id: str,
    user_id: str | None = None,
    current_user: models.User | None = Depends(get_current_user_optional),
    service: WsRoomService = Depends(get_ws_room_service),
):
    try:
        return await service.start_room(room_id=room_id, user_id=user_id, current_user=current_user)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rooms/{room_id}")
def get_room(
    room_id: str,
    service: Annotated[WsRoomService, Depends(get_ws_room_service)],
):
    try:
        return service.get_room(room_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ─────────────────── WebSocket ────────────────────────────────


@router.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """
    WebSocket-соединение для участника комнаты.
    Аутентификация: передать ?token=<JWT> в query-параметрах.

    Поддерживаемые входящие сообщения:
      - {"type": "PING"} → ответ {"type": "PONG"}

    Исходящие события (сервер → клиент):
      - ROOM_STATE          — полное состояние комнаты при подключении
      - PLAYER_JOINED       — кто-то подключился
      - PLAYER_DISCONNECTED — кто-то отключился
      - GAME_STARTED        — хост запустил игру
      - ERROR               — ошибка обработки сообщения
    """

    ws_service = WsRoomService(
        db=db,
        room_manager=room_manager,
        connection_manager=conn_manager,
    )

    # ── Аутентификация: токен обязателен только для зарегистрированных ──
    room = ws_service.ensure_runtime_room(room_id)
    if room is None or user_id not in room.participants:
        # Необходим accept() перед close() — иначе коды закрытия не доставляются клиенту
        await websocket.accept()
        await websocket.close(code=4004, reason="Комната или участник не найдены")
        return

    participant = room.participants[user_id]
    token = websocket.query_params.get("token")

    # Для зарегистрированных пользователей токен обязателен
    auth_error = validate_ws_participant_token(participant, token)
    if auth_error is not None:
        await websocket.accept()
        await websocket.close(code=4001, reason=auth_error)
        return

    if not ws_service.validate_db_membership(
        room_id=room_id,
        user_id=user_id,
        participant=participant,
    ):
        await websocket.accept()
        await websocket.close(code=4001, reason="Пользователь не состоит в игровой сессии")
        return

    # ── Подключение ──
    try:
        await conn_manager.connect(user_id, websocket)
    except Exception as exc:
        logger.error("WebSocket accept failed for %s: %s", user_id, exc, exc_info=True)
        try:
            await websocket.close(code=1011, reason="Server error")
        except RuntimeError:
            logger.warning("WebSocket уже закрыт после ошибки accept для %s", user_id)
        return

    room_manager.set_connected(room_id, user_id, True)

    # Отправляем подключившемуся полное состояние комнаты
    try:
        await conn_manager.send(user_id, serialize_room_state(room.to_dict()))
    except Exception as exc:
        logger.error("Не удалось отправить ROOM_STATE для %s: %s", user_id, exc, exc_info=True)

    # Уведомляем остальных о новом подключении
    others = [uid for uid in room_manager.participant_ids(room_id) if uid != user_id]
    join_results = await conn_manager.broadcast(
        others,
        serialize_player_joined(
            user_id=user_id,
            username=participant.username,
            is_guest=participant.is_guest,
        ),
    )
    join_failed = [uid for uid, success in join_results.items() if not success]
    if join_failed:
        logger.error(
            "Не удалось отправить PLAYER_JOINED %s пользователям: %s",
            len(join_failed),
            join_failed,
        )

    # ── Цикл обработки сообщений ──
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                # Клиент прислал невалидный JSON — не роняем соединение
                await conn_manager.send(
                    user_id,
                    serialize_error("Невалидный JSON"),
                )
                continue

            try:
                PingMessage.model_validate(data)
            except ValidationError:
                await conn_manager.send(
                    user_id,
                    serialize_error("Невалидное сообщение"),
                )
                continue

            await conn_manager.send(user_id, serialize_pong())

    except WebSocketDisconnect:
        logger.info("Пользователь %s отключился от комнаты %s", user_id, room_id)
    except Exception as exc:
        # Ловим любую непредвиденную ошибку, чтобы не уронить сервер
        logger.error(
            "Непредвиденная ошибка в WebSocket для %s в комнате %s: %s",
            user_id, room_id, exc,
        )
    finally:
        # Гарантированная очистка при любом завершении
        try:
            conn_manager.disconnect(user_id)
            room_manager.set_connected(room_id, user_id, False)
            current_others = [uid for uid in room_manager.participant_ids(room_id) if uid != user_id]
            if current_others:
                results = await conn_manager.broadcast(
                    current_others,
                    serialize_player_disconnected(user_id),
                )
                failed = [uid for uid, success in results.items() if not success]
                if failed:
                    logger.error(
                        "Не удалось отправить PLAYER_DISCONNECTED %s пользователям: %s",
                        len(failed),
                        failed,
                    )
            logger.info("Пользователь %s отключён от комнаты %s", user_id, room_id)
        except Exception as exc:
            logger.error(
                "Ошибка cleanup для пользователя %s в комнате %s: %s",
                user_id,
                room_id,
                exc,
                exc_info=True,
            )
            try:
                room_manager.set_connected(room_id, user_id, False)
            except Exception as retry_exc:
                logger.error(
                    "Повторная попытка set_connected(false) провалена для %s: %s",
                    user_id,
                    retry_exc,
                    exc_info=True,
                )
