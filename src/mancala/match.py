"""Stateful wrapper around a Rules implementation for interactive play."""

from mancala.events import Event
from mancala.rules import IllegalMoveError, Move, MoveResult, Rules
from mancala.state import GameState, Player


class Match:
    """Holds the current state of one game and validates moves.

    Also threads the set of previously seen states into `Rules.apply_move`,
    which is how variants with repetition rules (Oware) detect cycles — so
    every game played through Match terminates.
    """

    def __init__(self, rules: Rules, state: GameState | None = None) -> None:
        self.rules = rules
        self._state = state if state is not None else rules.initial_state()
        if not rules.is_over(self._state) and not rules.legal_moves(self._state):
            raise ValueError(
                "unresolved state: no legal moves but not over; "
                "pass states produced by initial_state or apply_move"
            )
        self._seen: set[GameState] = {self._state}
        self._history: list[tuple[GameState, Move, tuple[Event, ...]]] = []

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def history(self) -> tuple[tuple[GameState, Move, tuple[Event, ...]], ...]:
        return tuple(self._history)

    @property
    def is_over(self) -> bool:
        return self.rules.is_over(self._state)

    @property
    def winner(self) -> Player | None:
        return self.rules.winner(self._state)

    def play(self, move: Move) -> MoveResult:
        if self.is_over:
            raise IllegalMoveError("the game is over")
        if move not in self.rules.legal_moves(self._state):
            raise IllegalMoveError(f"cup {move + 1} is not a legal move")
        result = self.rules.apply_move(self._state, move, self._seen)
        self._history.append((self._state, move, result.events))
        self._state = result.state
        self._seen.add(result.state)
        return result
