"""The Rules protocol every variant implements, plus shared result types."""

from collections.abc import Container
from typing import NamedTuple, Protocol

from pydantic import BaseModel

from mancala.engine.events import Event
from mancala.engine.state import GameState, Player

type Move = int
"""A move is a 0-based cup index from the mover's own perspective."""


class MoveResult(NamedTuple):
    state: GameState
    events: tuple[Event, ...]


class IllegalMoveError(Exception):
    """The attempted move is not legal in the current state."""


class Rules(Protocol):
    """The mechanics of one mancala variant, configured for one game.

    A variant is constructed with its config and holds nothing about the game
    in progress. `apply_move` assumes the move is legal (validate via `Match`)
    and returns a fully resolved state: sowing, captures, turn passing, and the
    end-of-game sweep if the move ended the game. `history` holds the states
    already seen this game; variants with repetition rules (Oware) consult it,
    others ignore it. Terminal states have every cup empty, so `is_over` and
    `winner` are pure functions of a single state.
    """

    # A property, not an attribute: a protocol attribute is invariant, so
    # `config: BaseModel` could not be satisfied by a variant's own config type.
    @property
    def config(self) -> BaseModel: ...

    def initial_state(self) -> GameState: ...

    def legal_moves(self, state: GameState) -> tuple[Move, ...]: ...

    def apply_move(
        self,
        state: GameState,
        move: Move,
        history: Container[GameState] = frozenset(),
    ) -> MoveResult: ...

    def is_over(self, state: GameState) -> bool: ...

    def winner(self, state: GameState) -> Player | None: ...
