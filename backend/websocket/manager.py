"""
Менеджер WebSocket-соединений.
Хранит активные соединения и предоставляет методы для отправки
сообщений конкретному пользователю или группе.
"""

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NoActiveWebSocketError(ConnectionError):
    """Ожидаемая ошибка: у пользователя нет активного WebSocket."""



class ConnectionManager:
    def __init__(self):
        # Маппинг user_id → активный WebSocket
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Принимает WebSocket-соединение и регистрирует его за user_id."""
        await websocket.accept()
        self.connections[user_id] = websocket

    def disconnect(self, user_id: str) -> None:
        """Удаляет соединение из реестра."""
        self.connections.pop(user_id, None)

    async def send(self, user_id: str, message: dict[str, Any]) -> None:
        """Отправляет JSON-сообщение конкретному пользователю."""
        ws = self.connections.get(user_id)
        if ws is None:
            raise NoActiveWebSocketError(f"No active websocket for user_id={user_id}")

        try:
            await ws.send_json(message)
        except Exception as exc:
            logger.warning(
                "Не удалось отправить сообщение пользователю %s: %s",
                user_id,
                exc,
            )
            self.disconnect(user_id)
            raise

    async def broadcast(
        self,
        user_ids: list[str],
        message: dict[str, Any],
    ) -> dict[str, bool]:
        """Рассылает JSON-сообщение списку пользователей и возвращает статус по каждому."""
        results: dict[str, bool] = {}
        for user_id in user_ids:
            try:
                await self.send(user_id, message)
                results[user_id] = True
            except NoActiveWebSocketError as exc:
                logger.warning("Broadcast skipped for %s: %s", user_id, exc)
                results[user_id] = False
            except Exception as exc:
                logger.error("Broadcast failed for %s: %s", user_id, exc, exc_info=True)
                results[user_id] = False
        return results
