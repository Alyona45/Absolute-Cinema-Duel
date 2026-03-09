"""
Роутер для WebSocket-эндпоинтов и HTTP-управления комнатами.
Поддерживает авторизованных пользователей и гостей.
"""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from backend import models, settings
from backend.security import get_current_user
from backend.websocket.manager import ConnectionManager
from backend.websocket.room import RoomManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Синглтоны — живут пока работает сервер
conn_manager = ConnectionManager()
room_manager = RoomManager()


# ─────────────────── Аутентификация для WebSocket ─────────────────


def authenticate_ws_token(token: str) -> str | None:
    """
    Проверяет JWT access-токен, переданный через query-параметр WebSocket.
    Возвращает email пользователя или None при невалидном токене.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if email is None or token_type != "access":
            return None
        return email
    except JWTError:
        return None


# ─────────────────── HTTP эндпоинты (авторизованные) ──────────


@router.post("/rooms", status_code=201)
def create_room(
    current_user: Annotated[models.User, Depends(get_current_user)],
):
    """Создаёт новую комнату. Текущий пользователь становится хостом."""
    username = current_user.username or current_user.email
    room_id, user_id = room_manager.create_room(username, is_guest=False)
    return {"room_id": room_id, "user_id": user_id}


@router.post("/rooms/{room_id}/join", status_code=201)
def join_room(
    room_id: str,
    current_user: Annotated[models.User, Depends(get_current_user)],
):
    """Присоединяет авторизованного пользователя к комнате."""
    username = current_user.username or current_user.email
    user_id = room_manager.join_room(room_id, username, is_guest=False)
    if user_id is None:
        raise HTTPException(404, "Комната не найдена или игра уже началась")
    return {"user_id": user_id}


# ─────────────────── HTTP эндпоинты (гостевые) ───────────────


class GuestBody(BaseModel):
    """Тело запроса для гостевого входа. Имя опциональное."""
    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
        description="Имя гостя. Если не указано — генерируется автоматически.",
    )


def _guest_username(name: str | None) -> str:
    """Формирует имя гостя: пользовательское или сгенерированное."""
    if name:
        return name
    return f"Гость_{uuid.uuid4().hex[:6]}"


@router.post("/rooms/guest", status_code=201)
def create_room_guest(body: GuestBody):
    """Создаёт комнату от имени гостя (без авторизации)."""
    username = _guest_username(body.username)
    room_id, user_id = room_manager.create_room(username, is_guest=True)
    return {"room_id": room_id, "user_id": user_id, "username": username}


@router.post("/rooms/{room_id}/join/guest", status_code=201)
def join_room_guest(room_id: str, body: GuestBody):
    """Присоединяет гостя к комнате (без авторизации)."""
    username = _guest_username(body.username)
    user_id = room_manager.join_room(room_id, username, is_guest=True)
    if user_id is None:
        raise HTTPException(404, "Комната не найдена или игра уже началась")
    return {"user_id": user_id, "username": username}


# ─────────────────── Общие HTTP эндпоинты ─────────────────────


@router.post("/rooms/{room_id}/start")
async def start_room(
    room_id: str,
    user_id: str,
):
    """
    Запускает игру в комнате. Только хост может вызвать.
    user_id — ID участника в комнате (полученный при создании).
    Рассылает GAME_STARTED всем участникам через WebSocket.
    """
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(404, "Комната не найдена")

    # Проверяем что вызывающий — хост комнаты
    if room.host_user_id != user_id:
        raise HTTPException(403, "Только хост может запустить игру")

    ok = room_manager.start_game(room_id)
    if not ok:
        raise HTTPException(400, "Невозможно начать игру (неверный статус комнаты)")

    # Уведомляем всех участников о старте
    participants = room_manager.participant_ids(room_id)
    await conn_manager.broadcast(participants, {
        "type": "GAME_STARTED",
        "payload": {"room_id": room_id},
    })
    return {"status": "ok"}


@router.get("/rooms/{room_id}")
def get_room(room_id: str):
    """Возвращает текущее состояние комнаты."""
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(404, "Комната не найдена")
    return room.to_dict()


# ─────────────────── WebSocket ────────────────────────────────


@router.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
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

    # ── Аутентификация: токен обязателен только для зарегистрированных ──
    room = room_manager.get_room(room_id)
    if room is None or user_id not in room.participants:
        await websocket.close(code=4004, reason="Комната или участник не найдены")
        return

    participant = room.participants[user_id]
    token = websocket.query_params.get("token")

    # Для зарегистрированных пользователей токен обязателен
    if not participant.is_guest:
        if not token or authenticate_ws_token(token) is None:
            await websocket.close(code=4001, reason="Невалидный или отсутствующий токен")
            return

    # ── Подключение ──
    try:
        await conn_manager.connect(user_id, websocket)
    except Exception as exc:
        logger.error("Ошибка при accept WebSocket для %s: %s", user_id, exc)
        return

    room_manager.set_connected(room_id, user_id, True)
    participants = room_manager.participant_ids(room_id)
    others = [uid for uid in participants if uid != user_id]

    # Отправляем подключившемуся полное состояние комнаты
    try:
        await conn_manager.send(user_id, {
            "type": "ROOM_STATE",
            "payload": room.to_dict(),
        })
    except Exception as exc:
        logger.error("Не удалось отправить ROOM_STATE для %s: %s", user_id, exc)

    # Уведомляем остальных о новом подключении
    await conn_manager.broadcast(others, {
        "type": "PLAYER_JOINED",
        "payload": {
            "user_id": user_id,
            "username": participant.username,
            "is_guest": participant.is_guest,
        },
    })

    # ── Цикл обработки сообщений ──
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                # Клиент прислал невалидный JSON — не роняем соединение
                await conn_manager.send(user_id, {
                    "type": "ERROR",
                    "payload": {"message": "Невалидный JSON"},
                })
                continue

            msg_type = data.get("type")

            if msg_type == "PING":
                await conn_manager.send(user_id, {"type": "PONG"})
            else:
                # Неизвестный тип сообщения — сообщаем клиенту
                await conn_manager.send(user_id, {
                    "type": "ERROR",
                    "payload": {"message": f"Неизвестный тип сообщения: {msg_type}"},
                })

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
        conn_manager.disconnect(user_id)
        room_manager.set_connected(room_id, user_id, False)
        await conn_manager.broadcast(others, {
            "type": "PLAYER_DISCONNECTED",
            "payload": {"user_id": user_id},
        })
