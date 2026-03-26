from __future__ import annotations

import os


class TournamentSettings:
    """Runtime settings for the MovieCO tournament module."""

    def __init__(self) -> None:
        self.default_bracket_size: int = int(os.getenv("MOVIECO_DEFAULT_BRACKET_SIZE", "16"))
        self.max_bracket_size: int = int(os.getenv("MOVIECO_MAX_BRACKET_SIZE", "16"))


settings = TournamentSettings()
