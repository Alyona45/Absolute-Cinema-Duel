import pytest
from backend.services.flappy_service import FlappyGame


def test_flappy_game_basic_flow():
    game = FlappyGame(["p1", "p2"])
    game.start()
    assert game.running
    # Оба игрока живы
    assert all(p.alive for p in game.players.values())
    # Прыжок первого игрока
    game.handle_jump("p1")
    v_before = game.players["p1"].velocity
    game.tick()
    # После тика скорость изменилась (гравитация)
    assert game.players["p1"].velocity > v_before
    # Симулируем падение до смерти
    for _ in range(100):
        game.tick()
    # Оба игрока должны быть мертвы
    assert not any(p.alive for p in game.players.values())
    assert game.is_game_over()
    # Победитель — с максимальным score (или любой, если равенство)
    winner = game.get_winner()
    assert winner in ("p1", "p2")
