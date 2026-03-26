"""
WebSocket endpoint для Flappy Bird.

Правильный флоу:
  1. POST /sessions/            → создаёт сессию, возвращает invite_code, ставит guest cookie
  2. POST /sessions/join-by-code → второй игрок заходит по invite_code (тоже получает cookie)
  3. ws://.../ws/game/flappy/{invite_code}            — гость (токен из cookie)
     ws://.../ws/game/flappy/{invite_code}?token=JWT  — зарегистрированный пользователь
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from backend.actors import GUEST_TOKEN_COOKIE, CurrentActor, runtime_user_id_for_actor
from backend import settings
from backend.crud.user import get_user_by_email
from backend.database import SessionLocal
from backend.routers.ws import conn_manager, room_manager
from backend.schemas.game_flappy import (
    FlappyGameOverMsg,
    FlappyGameStateMsg,
    FlappyJumpEvent,
    FlappyPipeState,
    FlappyPlayerState,
)
from backend.security import decode_guest_token
from backend.websocket.auth import validate_ws_participant_token
from backend.websocket.service import WsRoomService

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory: invite_code -> FlappyGame
_flappy_games: dict[str, object] = {}


def _decode_access_token_to_actor(token: str) -> CurrentActor | None:
    """Декодирует access JWT зарегистрированного пользователя в CurrentActor."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if email is None or token_type != "access":
            return None
    except JWTError:
        return None

    db = SessionLocal()
    try:
        user = get_user_by_email(db, email)
        if user is None:
            return None
        return CurrentActor(
            user_id=user.id,
            guest_id=None,
            display_name=user.username or user.email,
            email=user.email,
        )
    finally:
        db.close()


@router.websocket("/ws/game/flappy/{invite_code}")
async def flappy_ws(websocket: WebSocket, invite_code: str):
    # ── 1. Аутентификация ─────────────────────────────────────────────────────
    query_token = websocket.query_params.get("token")
    actor: CurrentActor | None = None

    if query_token:
        actor = _decode_access_token_to_actor(query_token)

    if actor is None:
        # Гость: токен из cookie
        cookie_header = websocket.headers.get("cookie", "")
        guest_token = None
        for part in cookie_header.split(";"):
            part = part.strip()
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            if k.strip() == GUEST_TOKEN_COOKIE:
                guest_token = v.strip()
                break
        if guest_token:
            actor = decode_guest_token(guest_token)

    if actor is None:
        await websocket.accept()
        await websocket.close(
            code=4001,
            reason="Требуется аутентификация: cookie guest_token или ?token=<JWT>",
        )
        return

    # ── 2. Runtime user_id ────────────────────────────────────────────────────
    try:
        user_id = runtime_user_id_for_actor(actor)
    except Exception:
        await websocket.accept()
        await websocket.close(code=4001, reason="Неверный actor")
        return

    # ── 3. Комната — ищем по invite_code, при необходимости восстанавливаем из БД
    db = SessionLocal()
    try:
        ws_service = WsRoomService(db=db, room_manager=room_manager, connection_manager=conn_manager)
        room = ws_service.ensure_runtime_room(invite_code)
    finally:
        db.close()

    if room is None:
        await websocket.accept()
        await websocket.close(code=4004, reason="Комната не найдена")
        return

    if user_id not in room.participants:
        await websocket.accept()
        await websocket.close(code=4004, reason="Вы не являетесь участником этой сессии")
        return

    # ── 4. Проверка JWT для зарегистрированных пользователей ─────────────────
    participant = room.participants[user_id]
    auth_error = validate_ws_participant_token(participant, query_token)
    if auth_error is not None:
        await websocket.accept()
        await websocket.close(code=4001, reason=auth_error)
        return

    # ── 5. Подключаем сокет ───────────────────────────────────────────────────
    await conn_manager.connect(user_id, websocket)
    room_manager.set_connected(invite_code, user_id, True)

    try:
        # ── 6. Создаём или получаем игру ──────────────────────────────────────
        from backend.services.flappy_service import FlappyGame, FlappyPlayer  # noqa: PLC0415

        game: FlappyGame = _flappy_games.get(invite_code)  # type: ignore[assignment]
        if game is None:
            player_ids = list(room.participants.keys())
            game = FlappyGame(player_ids)
            # Don't auto-start - wait for room.start endpoint
            _flappy_games[invite_code] = game
        elif user_id not in game.players:
            game.players[user_id] = FlappyPlayer(id=user_id)

        # ── 7. Игровой цикл ───────────────────────────────────────────────────
        send_task = asyncio.create_task(_send_game_state_loop(websocket, game))
        recv_task = asyncio.create_task(_recv_events_loop(websocket, game, user_id))
        await asyncio.wait([send_task, recv_task], return_when=asyncio.FIRST_COMPLETED)

        for task in [send_task, recv_task]:
            if not task.done():
                task.cancel()

        # ── 8. Game over ──────────────────────────────────────────────────────
        if game.is_game_over():
            winner = game.get_winner()
            msg = FlappyGameOverMsg(
                winner_id=winner,
                scores={pid: p.score for pid, p in game.players.items()},
            )
            try:
                await websocket.send_json(msg.model_dump())
            except Exception:
                pass
            _flappy_games.pop(invite_code, None)

    except WebSocketDisconnect:
        logger.info("Игрок %s отключился от flappy/%s", user_id, invite_code)
    except Exception as exc:
        logger.error("Ошибка в flappy WS для %s: %s", user_id, exc, exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
        raise
    finally:
        conn_manager.disconnect(user_id)
        room_manager.set_connected(invite_code, user_id, False)


async def _send_game_state_loop(websocket: WebSocket, game) -> None:
    while not game.is_game_over():
        state = FlappyGameStateMsg(
            players={
                pid: FlappyPlayerState(**p.model_dump())
                for pid, p in game.players.items()
            },
            pipes=[FlappyPipeState(**pipe.model_dump()) for pipe in game.pipes],
            tick=game.tick_count,
            running=game.running,
        )
        try:
            await websocket.send_json(state.model_dump())
        except Exception:
            return
        await asyncio.sleep(game.TICK_RATE)
        game.tick()


async def _recv_events_loop(websocket: WebSocket, game, player_id: str) -> None:
    while not game.is_game_over():
        try:
            data = await websocket.receive_json()
        except Exception:
            return
        try:
            event = FlappyJumpEvent(**data)
        except Exception:
            continue
        if event.action == "jump" and event.player_id == player_id:
            game.handle_jump(player_id)