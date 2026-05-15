from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from backend.tournaments.room_bus import RoomBus
from backend.tournaments.schemas import (
    TournamentJoinRequest,
    TournamentRoomCreate,
    TournamentRoomCreated,
    TournamentTestPresetCreate,
    TournamentJoinedResponse,
    WsPingEvent,
    WsVoteEvent,
)
from backend.tournaments.service import TournamentService

router = APIRouter(prefix="/tournaments", tags=["movieco"])

_bus = RoomBus()
_service = TournamentService(bus=_bus)
_room_sockets: dict[int, set[WebSocket]] = defaultdict(set)
_room_subscribed: set[int] = set()
_hub_lock = asyncio.Lock()


async def _broadcast_local(room_id: int, message: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    for ws in list(_room_sockets.get(room_id, set())):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _room_sockets[room_id].discard(ws)


async def _ensure_subscribed(room_id: int) -> None:
    async with _hub_lock:
        if room_id in _room_subscribed:
            return

        async def _handler(payload: dict) -> None:
            await _broadcast_local(room_id, payload)

        try:
            await _bus.subscribe(str(room_id), _handler)
            _room_subscribed.add(room_id)
        except Exception:
            # Event sync should never block API operations.
            return


@router.post("/tests", response_model=dict)
async def create_test_preset(body: TournamentTestPresetCreate) -> dict:
    try:
        return await _service.create_preset(body.name, body.criteria)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/catalog/import", response_model=dict)
async def import_catalog(query: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)) -> dict:
    try:
        return await _service.import_movies_from_kinopoisk(query=query, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/catalog/seed-demo", response_model=dict)
async def seed_demo_movies(count: int = Query(16, ge=2, le=256)) -> dict:
    try:
        return await _service.seed_demo_movies(target_count=count)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tests", response_model=list[dict])
async def list_test_presets() -> list[dict]:
    return await _service.list_presets()


@router.post("/rooms", response_model=TournamentRoomCreated, status_code=201)
async def create_room(body: TournamentRoomCreate) -> TournamentRoomCreated:
    try:
        room_id, user_key, room_state = await _service.create_room(
            title=body.title,
            display_name=body.display_name,
            bracket_size=body.bracket_size,
            preset_id=body.preset_id,
            criteria=body.criteria,
            host_user_id=None,
            session_movie_ids=body.session_movie_ids,
        )
        return TournamentRoomCreated(room_id=room_id, user_key=user_key, room=room_state)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rooms", response_model=list[dict])
async def list_rooms(limit: int = Query(20, ge=1, le=100), status: str = Query("LOBBY")) -> list[dict]:
    only_lobby = status.upper() == "LOBBY"
    return await _service.list_rooms(limit=limit, only_lobby=only_lobby)


@router.post("/rooms/{room_id}/join", response_model=TournamentJoinedResponse, status_code=201)
async def join_room(room_id: int, body: TournamentJoinRequest) -> TournamentJoinedResponse:
    try:
        user_key, room_state = await _service.join_room(room_id, body.display_name, None)
        try:
            await _bus.publish(str(room_id), {"type": "room_state", "payload": room_state.model_dump()})
        except Exception:
            pass
        return TournamentJoinedResponse(room_id=room_id, user_key=user_key, room=room_state)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rooms/{room_id}", response_model=dict)
async def get_room(room_id: int) -> dict:
    try:
        room_state = await _service.get_room_state(room_id)
        return room_state.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/rooms/{room_id}/start", response_model=dict)
async def start_room(room_id: int, user_key: str = Query(..., min_length=8)) -> dict:
    try:
        room_state = await _service.start_room(room_id, user_key)
        return room_state.model_dump()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.websocket("/ws/{room_id}")
async def tournament_ws(websocket: WebSocket, room_id: int):
    user_key = websocket.query_params.get("user_key")
    print(f"[WS] Connect attempt: room_id={room_id}, user_key={user_key[:10]}..." if user_key else f"[WS] Connect attempt: room_id={room_id}, no user_key")
    
    if not user_key:
        await websocket.accept()
        await websocket.close(code=4001, reason="user_key query parameter is required")
        return

    try:
        room_state = await _service.get_room_state(room_id)
        print(f"[WS] Room loaded: participants={len(room_state.participants)}")
    except Exception as e:
        print(f"[WS] Failed to load room: {e}")
        await websocket.accept()
        await websocket.close(code=4004, reason="Room not found")
        return

    participants = {item.user_key for item in room_state.participants}
    if user_key not in participants:
        print(f"[WS] User key not in participants. Key={user_key[:10]}..., participants={len(participants)}")
        await websocket.accept()
        await websocket.close(code=4003, reason="Participant is not in this room")
        return

    print(f"[WS] User authenticated, accepting connection")
    await websocket.accept()
    await _ensure_subscribed(room_id)
    _room_sockets[room_id].add(websocket)
    print(f"[WS] WebSocket registered for room {room_id}")

    try:
        await websocket.send_json({"type": "room_state", "payload": room_state.model_dump()})
        print(f"[WS] Sent initial room_state")
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            print(f"[WS] Received: type={event_type}")
            if event_type == "ping":
                WsPingEvent(**data)
                await websocket.send_json({"type": "pong", "payload": {}})
                continue
            if event_type != "vote":
                await websocket.send_json({"type": "error", "payload": {"detail": "Unknown event type"}})
                continue

            event = WsVoteEvent(**data)
            print(f"[WS] Processing vote: movie_id={event.movie_id}")
            state = await _service.submit_vote(room_id, user_key, event.movie_id)
            await websocket.send_json({"type": "vote_accepted", "payload": state.model_dump()})
            print(f"[WS] Vote processed")

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected")
    except Exception as exc:
        print(f"[WS] Exception: {exc}")
        try:
            await websocket.send_json({"type": "error", "payload": {"detail": str(exc)}})
        except Exception:
            pass
    finally:
        _room_sockets[room_id].discard(websocket)
        print(f"[WS] Cleaned up")
