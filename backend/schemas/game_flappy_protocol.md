"""
WebSocket protocol and game flow for Flappy Bird multiplayer (Absolute Cinema Duel)

1. После выбора фильма хост вызывает POST /sessions/{session_id}/start-game
   - Сессия переходит в статус PLAYING
2. Все участники подключаются к WS /ws/game/flappy/{session_id}
   - Сервер рассылает состояние игры (type: "state")
   - Клиенты отправляют action: "jump" (только за себя)
3. После завершения игры сервер отправляет type: "game_over" с winner_id и score
4. Победитель фиксируется через стандартный pick_winner (или автоматически)

Протокол сообщений:

Клиент → Сервер:
{
  "action": "jump",
  "player_id": "..."  # всегда свой id
}

Сервер → Клиент (каждый тик):
{
  "type": "state",
  "players": { "id": { ... } },
  "pipes": [ ... ],
  "tick": N,
  "running": true/false
}

Сервер → Клиент (конец игры):
{
  "type": "game_over",
  "winner_id": "...",
  "scores": { "id": score }
}

Архитектура оставляет пространство для выбора других игр после этапа выбора фильма.
"""
