from __future__ import annotations

import random


def normalize_bracket_size(size: int) -> int:
    allowed = [2, 4, 8, 16]
    for value in allowed:
        if size <= value:
            return value
    return 16


def round_name(round_no: int, total_rounds: int) -> str:
    remaining = 2 ** (total_rounds - round_no + 1)
    names = {
        16: "1/8 final",
        8: "1/4 final",
        4: "1/2 final",
        2: "Final",
    }
    return names.get(remaining, f"Round {round_no}")


def build_initial_pairs(movie_ids: list[int], bracket_size: int) -> list[list[int]]:
    if len(movie_ids) < bracket_size:
        raise ValueError("Not enough movies to build bracket")

    picked = random.sample(movie_ids, bracket_size)
    random.shuffle(picked)
    pairs: list[list[int]] = []
    for idx in range(0, bracket_size, 2):
        pairs.append([picked[idx], picked[idx + 1]])
    return pairs


def total_rounds(bracket_size: int) -> int:
    current = bracket_size
    rounds = 0
    while current > 1:
        current //= 2
        rounds += 1
    return rounds


def progress_value(round_no: int, match_no: int, bracket_size: int) -> float:
    rounds = total_rounds(bracket_size)
    completed_rounds = max(round_no - 1, 0)
    base = completed_rounds / rounds
    matches_in_round = bracket_size // (2 ** round_no)
    if matches_in_round <= 0:
        return 1.0
    in_round = (match_no - 1) / matches_in_round
    return min(base + (in_round / rounds), 1.0)
