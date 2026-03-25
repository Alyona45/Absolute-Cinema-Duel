"""
Pydantic schemas for Flappy Bird multiplayer game WebSocket protocol.
- All input validated at boundary
- Versioned, extensible
"""

from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


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

class FlappyGameOverMsg(BaseModel):
    type: Literal["game_over"] = "game_over"
    winner_id: Optional[str]
    scores: Dict[str, int]

class FlappyJumpEvent(BaseModel):
    action: Literal["jump"] = "jump"
    player_id: str

# Union for incoming events (расширяемо)
FlappyClientEvent = FlappyJumpEvent

# Union for outgoing messages (расширяемо)
FlappyServerMsg = FlappyGameStateMsg | FlappyGameOverMsg
