"""Immutable game state shared by all variants."""

from enum import Enum
from typing import NamedTuple


class Player(Enum):
    SOUTH = 0
    NORTH = 1

    @property
    def opponent(self) -> "Player":
        return Player(1 - self.value)


class GameState(NamedTuple):
    """A complete position. board[p.value] holds Player(p)'s cups in sowing order."""

    board: tuple[tuple[int, ...], tuple[int, ...]]
    stores: tuple[int, int]
    current_player: Player
