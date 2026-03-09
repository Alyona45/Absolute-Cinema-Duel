"""
Менеджер комнат (in-memory).
Управляет жизненным циклом: создание, подключение, смена статуса, очистка.
"""

import time
import uuid

from backend.websocket.models import Participant, Room


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}

    # ─────────────────── Создание / подключение ───────────────────

    def create_room(self, host_username: str, is_guest: bool = False) -> tuple[str, str]:
        """
        Создаёт новую комнату.
        Возвращает (room_id, user_id) — хост автоматически добавляется
        как первый участник. is_guest — гостевой ли это пользователь.
        """
        room_id = uuid.uuid4().hex[:8]
        user_id = str(uuid.uuid4())
        room = Room(host_user_id=user_id)
        room.participants[user_id] = Participant(
            username=host_username, is_guest=is_guest,
        )
        room.last_activity = time.time()
        self.rooms[room_id] = room
        return room_id, user_id

    def join_room(self, room_id: str, username: str, is_guest: bool = False) -> str | None:
        """
        Добавляет участника в комнату.
        Возвращает user_id нового участника, или None если комната
        не найдена / игра уже началась. is_guest — гостевой ли это пользователь.
        """
        room = self.rooms.get(room_id)
        if room is None or room.status != "waiting":
            return None
        room.last_activity = time.time()
        user_id = str(uuid.uuid4())
        room.participants[user_id] = Participant(
            username=username, is_guest=is_guest,
        )
        return user_id

    # ─────────────────── Получение данных ─────────────────────────

    def get_room(self, room_id: str) -> Room | None:
        """Возвращает комнату по ID или None."""
        return self.rooms.get(room_id)

    def participant_ids(self, room_id: str) -> list[str]:
        """Возвращает список user_id всех участников комнаты."""
        room = self.rooms.get(room_id)
        return list(room.participants.keys()) if room else []

    # ─────────────────── Управление статусом ──────────────────────

    def start_game(self, room_id: str) -> bool:
        """
        Переводит комнату в статус 'playing'.
        Возвращает True при успехе, False если комната не найдена
        или не в статусе 'waiting'.
        """
        room = self.rooms.get(room_id)
        if room is None or room.status != "waiting":
            return False
        room.status = "playing"
        room.last_activity = time.time()
        return True

    def finish_game(self, room_id: str) -> bool:
        """
        Переводит комнату в статус 'finished'.
        Возвращает True при успехе.
        """
        room = self.rooms.get(room_id)
        if room is None or room.status != "playing":
            return False
        room.status = "finished"
        room.last_activity = time.time()
        return True

    # ─────────────────── Статус подключения ───────────────────────

    def set_connected(self, room_id: str, user_id: str, connected: bool):
        """Обновляет флаг connected для участника."""
        room = self.rooms.get(room_id)
        if room and user_id in room.participants:
            room.participants[user_id].connected = connected

    # ─────────────────── Очистка ──────────────────────────────────

    def cleanup_dead_rooms(self, max_inactive_seconds: int = 60) -> list[str]:
        """
        Удаляет комнаты, в которых все отключены и нет активности
        дольше max_inactive_seconds.
        Возвращает список удалённых room_id.
        """
        now = time.time()
        dead = []
        for rid, room in self.rooms.items():
            all_disconnected = all(
                not p.connected for p in room.participants.values()
            )
            if all_disconnected and (now - room.last_activity > max_inactive_seconds):
                dead.append(rid)

        for rid in dead:
            self.rooms.pop(rid, None)

        return dead
