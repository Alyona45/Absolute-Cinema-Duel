from __future__ import annotations

from collections.abc import Awaitable, Callable

RoomHandler = Callable[[dict], Awaitable[None]]


class RoomBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[RoomHandler]] = {}

    async def publish(self, room_key: str, payload: dict) -> None:
        handlers = list(self._handlers.get(room_key, []))
        for handler in handlers:
            await handler(payload)

    async def subscribe(self, room_key: str, handler: RoomHandler) -> None:
        current_handlers = self._handlers.setdefault(room_key, [])
        if handler not in current_handlers:
            current_handlers.append(handler)

    async def unsubscribe(self, room_key: str) -> None:
        self._handlers.pop(room_key, None)