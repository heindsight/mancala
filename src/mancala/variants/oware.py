"""Oware (Abapa rules): capture-by-twos-and-threes mancala."""

from mancala.rules import Move
from mancala.state import GameState, Player
from mancala.variants._common import CUPS


class Oware:
    name = "oware"

    def initial_state(self, seeds_per_cup: int = 4) -> GameState:
        if seeds_per_cup != 4:
            raise ValueError("oware is played with exactly 4 seeds per cup")
        row = (seeds_per_cup,) * CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        mover = state.current_player
        own = state.board[mover.value]
        moves = tuple(cup for cup, seeds in enumerate(own) if seeds)
        if any(state.board[mover.opponent.value]):
            return moves
        # Opponent is out of seeds: only a move that reaches their row feeds them.
        return tuple(cup for cup in moves if cup + own[cup] >= CUPS)
