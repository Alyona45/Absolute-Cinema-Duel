"""
Менеджер WebSocket-соединений.
Хранит активные соединения и предоставляет методы для отправки
сообщений конкретному пользователю или группе.
"""

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Маппинг user_id → активный WebSocket
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Принимает WebSocket-соединение и регистрирует его за user_id."""
        await websocket.accept()
        self.connections[user_id] = websocket

    def disconnect(self, user_id: str):
        """Удаляет соединение из реестра."""
        self.connections.pop(user_id, None)

    async def send(self, user_id: str, message: dict):
        """Отправляет JSON-сообщение конкретному пользователю."""
        ws = self.connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("Не удалось отправить сообщение пользователю %s: %s", user_id, exc)
                # Если отправка не удалась — считаем соединение мёртвым
                self.disconnect(user_id)

    async def broadcast(self, user_ids: list[str], message: dict):
        """Рассылает JSON-сообщение списку пользователей."""
        for user_id in user_ids:
            await self.send(user_id, message)
