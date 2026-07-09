"""Kalah: the classic store-and-capture mancala variant."""

from mancala.rules import Move
from mancala.state import GameState, Player
from mancala.variants._common import CUPS


class Kalah:
    name = "kalah"

    def initial_state(self, seeds_per_cup: int = 4) -> GameState:
        if not 3 <= seeds_per_cup <= 6:
            raise ValueError("kalah supports 3-6 seeds per cup")
        row = (seeds_per_cup,) * CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        own = state.board[state.current_player.value]
        return tuple(cup for cup, seeds in enumerate(own) if seeds)
