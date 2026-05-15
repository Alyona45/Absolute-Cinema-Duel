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
    FlappyReadyEvent,
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

        # ── 7. Игровой цикл (Централизованный для всей комнаты) ─────────────────
        if invite_code not in _flappy_tasks:
            _flappy_tasks[invite_code] = asyncio.create_task(
                _room_game_loop(invite_code, game, room_manager, conn_manager)
            )

        # Слушаем события (прыжки) только от этого конкретного игрока
        await _recv_events_loop(websocket, game, user_id)

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


_flappy_tasks: dict[str, asyncio.Task] = {}


async def _broadcast_phase(
    invite_code: str,
    phase: str,
    game,
    room_manager,
    conn_manager,
    *,
    participants: list[str],
    confirmed_ids: list[str] | None = None,
    ready_ids: list[str] | None = None,
) -> None:
    """
    Push a FlappyGameStateMsg carrying the current phase so the client
    can decide which overlay to render (confirm_wait / ready_wait /
    playing / game_over).
    """
    room = room_manager.get_room(invite_code)
    if not room:
        return
    state = FlappyGameStateMsg(
        players={
            pid: FlappyPlayerState(**p.model_dump())
            for pid, p in game.players.items()
        },
        pipes=[FlappyPipeState(**pipe.model_dump()) for pipe in game.pipes],
        tick=game.tick_count,
        running=game.running,
        phase=phase,
        participants=sorted(participants),
        confirmed_ids=sorted(confirmed_ids or []),
        ready_ids=sorted(ready_ids or []),
    )
    msg_dict = state.model_dump()
    await conn_manager.broadcast(list(room.participants.keys()), msg_dict)


def _fetch_confirmed_ids(invite_code: str) -> set[str]:
    """
    Read the set of runtime user-ids whose participants have picked
    their session movie (the FlappyFilms "Подтвердить выбор" action).
    """
    from backend.crud.game_session import get_game_session_by_invite_code  # noqa: PLC0415
    from backend.crud.session_participant import get_participants_by_session  # noqa: PLC0415
    from backend.actors import runtime_user_id_for_participant  # noqa: PLC0415

    db = SessionLocal()
    try:
        session = get_game_session_by_invite_code(db, invite_code)
        if session is None:
            return set()
        participants = get_participants_by_session(db, session.id)
        # Force refresh from DB — session-level cache inside SQLAlchemy
        # could otherwise serve stale data if another coroutine/request
        # just updated the row in a different Session.
        confirmed = set()
        observed = []
        for p in participants:
            try:
                db.refresh(p)
            except Exception:
                pass
            try:
                pid = runtime_user_id_for_participant(p)
            except ValueError:
                logger.warning(
                    "Flappy %s: participant id=%s has no user_id/guest_id, skipping",
                    invite_code,
                    p.id,
                )
                continue
            observed.append((pid, p.selected_session_movie_id))
            if p.selected_session_movie_id is not None:
                confirmed.add(pid)
        logger.info(
            "Flappy confirm check %s: observed=%s confirmed=%s",
            invite_code,
            observed,
            sorted(confirmed),
        )
        return confirmed
    finally:
        db.close()


async def _room_game_loop(invite_code: str, game, room_manager, conn_manager) -> None:
    logger.info("Запуск игрового цикла для комнаты %s", invite_code)

    # Bug 4a / 4b fix: the loop now has three explicit phases before the
    # actual gameplay tick loop. Phase 1 (confirm_wait) holds the game
    # in a non-running / non-losing state until every participant has
    # picked their movie. Phase 2 (ready_wait) waits for every player to
    # press "Готов". If confirmations are revoked during ready_wait we
    # drop back to phase 1 instead of starting the game prematurely.
    empty_since: float | None = None
    started = False
    last_log_tick = 0.0
    try:
        while not started:
            # ── Phase 1 — confirm_wait ─────────────────────────────
            while True:
                room = room_manager.get_room(invite_code)
                if not room:
                    logger.warning("Комната %s исчезла", invite_code)
                    return

                participants = list(room.participants.keys())
                connected_ids = [
                    pid for pid, p in room.participants.items() if p.connected
                ]

                if not connected_ids:
                    now = asyncio.get_event_loop().time()
                    if empty_since is None:
                        empty_since = now
                    elif now - empty_since > 5.0:
                        logger.info("Комната %s пуста. Завершаем цикл ожидания.", invite_code)
                        return
                    await asyncio.sleep(0.5)
                    continue
                empty_since = None

                confirmed_ids = _fetch_confirmed_ids(invite_code)

                now = asyncio.get_event_loop().time()
                if now - last_log_tick > 1.5:
                    logger.info(
                        "Flappy %s confirm_wait: participants=%s connected=%s confirmed=%s",
                        invite_code,
                        sorted(participants),
                        sorted(connected_ids),
                        sorted(confirmed_ids),
                    )
                    last_log_tick = now

                await _broadcast_phase(
                    invite_code,
                    "confirm_wait",
                    game,
                    room_manager,
                    conn_manager,
                    participants=participants,
                    confirmed_ids=sorted(confirmed_ids),
                    ready_ids=sorted(game.ready_ids),
                )

                if len(participants) >= 2 and confirmed_ids >= set(participants):
                    logger.info(
                        "Комната %s: все (%s) подтвердили фильм — переходим к Ready.",
                        invite_code,
                        len(participants),
                    )
                    break

                await asyncio.sleep(0.3)

            # ── Phase 2 — ready_wait ───────────────────────────────
            back_to_confirm = False
            while True:
                room = room_manager.get_room(invite_code)
                if not room:
                    return
                participants = set(room.participants.keys())

                # Drop stale ready_ids for participants who left the room.
                game.ready_ids &= participants

                confirmed_ids = _fetch_confirmed_ids(invite_code)
                if not (len(participants) >= 2 and confirmed_ids >= participants):
                    # Someone un-picked their movie — return to phase 1.
                    logger.info(
                        "Комната %s: участник отменил выбор, возвращаемся к confirm_wait",
                        invite_code,
                    )
                    back_to_confirm = True
                    break

                await _broadcast_phase(
                    invite_code,
                    "ready_wait",
                    game,
                    room_manager,
                    conn_manager,
                    participants=sorted(participants),
                    confirmed_ids=sorted(confirmed_ids),
                    ready_ids=sorted(game.ready_ids),
                )

                if game.ready_ids >= participants:
                    logger.info(
                        "Комната %s: все игроки готовы. СТАРТ!",
                        invite_code,
                    )
                    await asyncio.sleep(0.6)
                    game.start()
                    started = True
                    break

                await asyncio.sleep(0.3)

            if back_to_confirm:
                # Loop back to phase 1.
                continue

        # ── Phase 3 — playing ───────────────────────────────────────
        while not game.is_game_over():
            if game.running:
                game.tick()

            state = FlappyGameStateMsg(
                players={
                    pid: FlappyPlayerState(**p.model_dump())
                    for pid, p in game.players.items()
                },
                pipes=[FlappyPipeState(**pipe.model_dump()) for pipe in game.pipes],
                tick=game.tick_count,
                running=game.running,
                phase="playing",
                participants=sorted(game.players.keys()),
                confirmed_ids=sorted(game.players.keys()),
                ready_ids=sorted(game.ready_ids),
            )

            msg_dict = state.model_dump()

            room = room_manager.get_room(invite_code)
            if room:
                await conn_manager.broadcast(list(room.participants.keys()), msg_dict)

            await asyncio.sleep(game.TICK_RATE)

        # ── Phase 4 — game over ─────────────────────────────────────
        logger.info("Игра в комнате %s завершена. Обработка результатов...", invite_code)
        winner_runtime_id = game.get_winner()

        db = SessionLocal()
        try:
            from backend.crud.game_session import get_game_session_by_invite_code as get_gs_by_code  # noqa: PLC0415
            from backend.crud.session_participant import get_participants_by_session as get_ps  # noqa: PLC0415
            from backend.crud.game_session import set_winner as db_set_winner  # noqa: PLC0415
            from backend.models import SessionStatus as DBStatus  # noqa: PLC0415
            from backend.actors import runtime_user_id_for_participant as get_runtime_id  # noqa: PLC0415

            game_session = get_gs_by_code(db, invite_code)
            if game_session:
                db_participants = get_ps(db, game_session.id)
                winner_p = None
                for p in db_participants:
                    if get_runtime_id(p) == winner_runtime_id:
                        winner_p = p
                        break

                if winner_p and winner_p.selected_session_movie_id:
                    db_set_winner(db, game_session, winner_p.selected_session_movie_id)
                    logger.info(
                        "Победитель для %s установлен: %s (фильм ID %s)",
                        invite_code,
                        winner_runtime_id,
                        winner_p.selected_session_movie_id,
                    )

                game_session.status = DBStatus.FINISHED
                from sqlalchemy.sql import func  # noqa: PLC0415
                game_session.finished_at = func.now()
                db.commit()
                logger.info("Сессия %s переведена в статус FINISHED", invite_code)

        except Exception as e:
            logger.error("Ошибка при сохранении результатов игры %s: %s", invite_code, e, exc_info=True)
            db.rollback()
        finally:
            db.close()

        msg = FlappyGameOverMsg(
            winner_id=winner_runtime_id,
            scores={pid: p.score for pid, p in game.players.items()},
        )
        msg_dict = msg.model_dump()

        room = room_manager.get_room(invite_code)
        if room:
            await conn_manager.broadcast(list(room.participants.keys()), msg_dict)

    finally:
        _flappy_games.pop(invite_code, None)
        _flappy_tasks.pop(invite_code, None)


async def _recv_events_loop(websocket: WebSocket, game, player_id: str) -> None:
    while not game.is_game_over():
        try:
            data = await websocket.receive_json()
        except Exception:
            return

        action = data.get("action") if isinstance(data, dict) else None

        if action == "ready":
            # Bug 4b fix: accept the Ready action even before the game
            # is running — that's the whole point of the gate.
            try:
                event = FlappyReadyEvent(**data)
            except Exception:
                continue
            if event.player_id == player_id:
                game.ready_ids.add(player_id)
            continue

        if action == "jump":
            try:
                event = FlappyJumpEvent(**data)
            except Exception:
                continue
            if event.player_id == player_id:
                game.handle_jump(player_id)
            continue

        # Unknown action — ignore to keep the socket alive.