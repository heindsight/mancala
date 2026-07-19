"""The Rules protocol every variant implements, plus shared result types."""

from collections.abc import Container
from typing import NamedTuple, Protocol

from mancala.events import Event
from mancala.state import GameState, Player

type Move = int
"""A move is a 0-based cup index from the mover's own perspective."""


class MoveResult(NamedTuple):
    state: GameState
    events: tuple[Event, ...]


class IllegalMoveError(Exception):
    """The attempted move is not legal in the current state."""


class Rules(Protocol):
    """A stateless mancala variant.

    `apply_move` assumes the move is legal (validate via `Match`) and returns a
    fully resolved state: sowing, captures, turn passing, and the end-of-game
    sweep if the move ended the game. `history` holds the states already seen
    this game; variants with repetition rules (Oware) consult it, others
    ignore it. Terminal states have every cup empty, so `is_over` and
    `winner` are pure functions of a single state.
    """

    name: str

    def initial_state(self, seeds_per_cup: int = 4) -> GameState: ...

    def legal_moves(self, state: GameState) -> tuple[Move, ...]: ...

    def apply_move(
        self,
        state: GameState,
        move: Move,
        history: Container[GameState] = frozenset(),
    ) -> MoveResult: ...

    def is_over(self, state: GameState) -> bool: ...

    def winner(self, state: GameState) -> Player | None: ...
