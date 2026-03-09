"""
Менеджер WebSocket-соединений.
Хранит активные соединения и предоставляет методы для отправки
сообщений конкретному пользователю или группе.
"""

from fastapi import WebSocket


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
            except Exception:
                # Если отправка не удалась — считаем соединение мёртвым
                self.disconnect(user_id)

    async def broadcast(self, user_ids: list[str], message: dict):
        """Рассылает JSON-сообщение списку пользователей."""
        for user_id in user_ids:
            await self.send(user_id, message)
