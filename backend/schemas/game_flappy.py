"""
Pydantic schemas for Flappy Bird multiplayer game WebSocket protocol.
- All input validated at boundary
- Versioned, extensible
"""

from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel


# Bug 4a / 4b fix: server-driven phases. Clients use this to decide
# which overlay to render before the actual canvas gameplay starts.
FlappyPhase = Literal["confirm_wait", "ready_wait", "playing", "game_over"]


class FlappyPlayerState(BaseModel):
    id: str
    y: float
    velocity: float
    alive: bool
    score: int


class FlappyPipeState(BaseModel):
    x: float
    gap_y: float
    width: float
    gap_height: float


class FlappyGameStateMsg(BaseModel):
    type: Literal["state"] = "state"
    players: Dict[str, FlappyPlayerState]
    pipes: List[FlappyPipeState]
    tick: int
    running: bool
    # Bug 4 fix: extra fields so the client can render the confirm/ready
    # overlays. They default to sensible empty values for backwards
    # compatibility with any cached state message shapes.
    phase: FlappyPhase = "playing"
    participants: List[str] = []
    confirmed_ids: List[str] = []
    ready_ids: List[str] = []


class FlappyGameOverMsg(BaseModel):
    type: Literal["game_over"] = "game_over"
    winner_id: Optional[str]
    scores: Dict[str, int]


class FlappyJumpEvent(BaseModel):
    action: Literal["jump"] = "jump"
    player_id: str


class FlappyReadyEvent(BaseModel):
    # Bug 4b fix: client emits this once the player hits the "Готов" button
    # on the ready_wait overlay. The server collects them in
    # `FlappyGame.ready_ids` and starts the actual game once every
    # connected participant has acknowledged.
    action: Literal["ready"] = "ready"
    player_id: str


# Union for incoming events (расширяемо)
FlappyClientEvent = FlappyJumpEvent | FlappyReadyEvent

# Union for outgoing messages (расширяемо)
FlappyServerMsg = FlappyGameStateMsg | FlappyGameOverMsg
