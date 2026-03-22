"""
Flappy Bird multiplayer game logic for Absolute Cinema Duel platform.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel
import random
import time


class FlappyPlayer(BaseModel):
    id: str
    y: float = 200.0
    velocity: float = 0.0
    alive: bool = True
    score: int = 0
    last_jump_ts: float = 0.0


class FlappyPipe(BaseModel):
    x: float
    gap_y: float
    width: float = 52.0
    gap_height: float = 120.0
    passed: bool = False  # флаг: труба уже засчитана как пройденная


class FlappyGameState(BaseModel):
    players: Dict[str, FlappyPlayer]
    pipes: List[FlappyPipe]
    tick: int
    running: bool


class FlappyGame:
    GRAVITY = 0.5
    JUMP_VELOCITY = -7.5
    PIPE_SPEED = 2.5
    PIPE_INTERVAL = 90       # тиков между трубами
    PIPE_START_X = 800.0     # правый край экрана
    GROUND_Y = 400.0
    BIRD_X = 150.0           # фиксированная x-позиция птицы (должна совпадать с фронтом)
    BIRD_RADIUS = 10.0
    TICK_RATE = 1 / 30       # 30 FPS

    def __init__(self, player_ids: List[str]):
        self.players: Dict[str, FlappyPlayer] = {
            pid: FlappyPlayer(id=pid) for pid in player_ids
        }
        self.pipes: List[FlappyPipe] = []
        self.tick_count: int = 0
        self.running: bool = True
        self._last_pipe_tick: int = 0

    def start(self) -> None:
        self._spawn_pipe()
        self.running = True
        self.tick_count = 0
        self._last_pipe_tick = 0

    def tick(self) -> None:
        if not self.running:
            return
        self.tick_count += 1

        # Обновляем позиции игроков
        for player in self.players.values():
            if not player.alive:
                continue
            player.velocity += self.GRAVITY
            player.y += player.velocity
            if player.y >= self.GROUND_Y:
                player.y = self.GROUND_Y
                player.alive = False
            elif player.y < 0:
                player.y = 0.0
                player.alive = False

        # Двигаем трубы
        for pipe in self.pipes:
            pipe.x -= self.PIPE_SPEED

        # Удаляем ушедшие за экран
        self.pipes = [p for p in self.pipes if p.x + p.width > 0]

        # Спавним новую трубу
        if self.tick_count - self._last_pipe_tick >= self.PIPE_INTERVAL:
            self._spawn_pipe()
            self._last_pipe_tick = self.tick_count

        # Коллизии и очки
        for player in self.players.values():
            if not player.alive:
                continue
            for pipe in self.pipes:
                if self._collides(player, pipe):
                    player.alive = False
                    break
                # Очко — когда птица прошла трубу (правый край трубы левее птицы)
                if not pipe.passed and pipe.x + pipe.width < self.BIRD_X:
                    pipe.passed = True
                    player.score += 1

        # Конец игры
        if all(not p.alive for p in self.players.values()):
            self.running = False

    def handle_jump(self, player_id: str) -> None:
        player = self.players.get(player_id)
        if player and player.alive:
            player.velocity = self.JUMP_VELOCITY
            player.last_jump_ts = time.time()

    def get_state(self) -> FlappyGameState:
        return FlappyGameState(
            players=self.players.copy(),
            pipes=self.pipes.copy(),
            tick=self.tick_count,
            running=self.running,
        )

    def is_game_over(self) -> bool:
        return not self.running

    def get_winner(self) -> Optional[str]:
        alive = [p for p in self.players.values() if p.alive]
        if alive:
            return None
        best = max(self.players.values(), key=lambda p: p.score, default=None)
        return best.id if best else None

    def _spawn_pipe(self) -> None:
        gap_y = random.uniform(80, self.GROUND_Y - self.BIRD_RADIUS * 2 - 80)
        self.pipes.append(FlappyPipe(x=self.PIPE_START_X, gap_y=gap_y))

    def _collides(self, player: FlappyPlayer, pipe: FlappyPipe) -> bool:
        px = self.BIRD_X
        py = player.y
        r = self.BIRD_RADIUS
        # Птица в зоне x трубы?
        if px + r > pipe.x and px - r < pipe.x + pipe.width:
            # Птица вне просвета?
            if not (pipe.gap_y + r < py < pipe.gap_y + pipe.gap_height - r):
                return True
        return False