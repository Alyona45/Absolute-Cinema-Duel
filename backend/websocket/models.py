"""
Модели данных для WebSocket-комнат (in-memory).
Структура комнаты и участников для real-time взаимодействия.
"""

import enum
import time
from dataclasses import dataclass, field
from typing import Optional


class RoomStatus(str, enum.Enum):
    """Statuses of an in-memory room."""
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass
class Participant:
    """Участник комнаты: имя, статус подключения, гость или нет."""
    username: str
    connected: bool = True
    is_guest: bool = False
    email: str | None = None  # Для зарегистрированных пользователей — для верификации JWT


@dataclass
class Room:
    """
    Игровая комната (in-memory).
    Хранит участников и статус для real-time взаимодействия через WebSocket.
    """
    host_user_id: str
    participants: dict[str, Participant] = field(default_factory=dict)
    status: RoomStatus = RoomStatus.WAITING
    last_activity: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Сериализация комнаты в словарь для отправки клиентам."""
        return {
            "host_user_id": self.host_user_id,
            "participants": {
                uid: {
                    "username": p.username,
                    "connected": p.connected,
                    "is_guest": p.is_guest,
                }
                for uid, p in self.participants.items()
            },
            "status": self.status.value,
        }
