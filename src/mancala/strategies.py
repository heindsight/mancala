"""Move-selection strategies for computer players, at three difficulty levels."""

import random
from collections.abc import Sequence
from math import inf
from typing import NamedTuple, Protocol

from mancala.match import Match
from mancala.rules import Move, Rules
from mancala.state import GameState, Player


class Strategy(Protocol):
    """Chooses a legal move for the current player of a match."""

    def choose(self, match: Match) -> Move: ...


class Chooser(Protocol):
    """The slice of `random.Random` a strategy needs to break ties."""

    def choice[T](self, seq: Sequence[T]) -> T: ...


class RandomStrategy:
    """Easy: plays a uniformly random legal move."""

    def __init__(self, rng: Chooser | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def choose(self, match: Match) -> Move:
        return self._rng.choice(match.rules.legal_moves(match.state))


class GreedyStrategy:
    """Medium: banks the most seeds this move; ties are broken randomly."""

    def __init__(self, rng: Chooser | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def choose(self, match: Match) -> Move:
        gains = {
            move: self._gain(match, move)
            for move in match.rules.legal_moves(match.state)
        }
        best = max(gains.values())
        return self._rng.choice([move for move, gain in gains.items() if gain == best])

    def _gain(self, match: Match, move: Move) -> int:
        mover = match.state.current_player
        after = match.rules.apply_move(match.state, move, match.seen).state
        return after.stores[mover.value] - match.state.stores[mover.value]


# Scores are (outcome, margin) pairs: outcome is the sign of a finished game's
# margin and 0 for unfinished positions, so in any variant a guaranteed win
# outranks any heuristic lead (and bigger wins outrank smaller).
type _Score = tuple[float, float]

_MIN: _Score = (-inf, -inf)
_MAX: _Score = (inf, inf)


class _Node(NamedTuple):
    """A position to search: how to play it, whose score it is, how it was reached."""

    rules: Rules
    me: Player
    state: GameState
    history: frozenset[GameState]

    @property
    def margin(self) -> int:
        stores = self.state.stores
        return stores[self.me.value] - stores[self.me.opponent.value]

    def child(self, move: Move) -> "_Node":
        after = self.rules.apply_move(self.state, move, self.history).state
        return self._replace(state=after, history=self.history | {after})


class MinimaxStrategy:
    """Hard: depth-limited minimax with alpha-beta pruning.

    Positions are scored by store difference, with finished games ranked
    above (won) or below (lost) every unfinished position. Extra turns are
    handled by switching between maximising and minimising on the state's
    actual mover rather than by ply parity, and the repetition history is
    extended along every simulated line. Root moves are searched with a full
    window so equally good moves score identically and ties can be broken
    randomly.
    """

    def __init__(self, depth: int = 6, rng: Chooser | None = None) -> None:
        if depth < 1:
            raise ValueError("depth must be at least 1")
        self._depth = depth
        self._rng = rng if rng is not None else random.Random()

    def choose(self, match: Match) -> Move:
        root = _Node(match.rules, match.state.current_player, match.state, match.seen)
        values = {
            move: self._value(root.child(move), self._depth - 1, _MIN, _MAX)
            for move in match.rules.legal_moves(match.state)
        }
        best = max(values.values())
        return self._rng.choice([m for m, value in values.items() if value == best])

    def _value(self, node: _Node, depth: int, alpha: _Score, beta: _Score) -> _Score:
        if node.rules.is_over(node.state):
            margin = node.margin
            return ((margin > 0) - (margin < 0), margin)
        if depth == 0:
            return (0, node.margin)
        maximising = node.state.current_player is node.me
        best = _MIN if maximising else _MAX
        for move in node.rules.legal_moves(node.state):
            score = self._value(node.child(move), depth - 1, alpha, beta)
            if maximising:
                best = max(best, score)
                alpha = max(alpha, score)
            else:
                best = min(best, score)
                beta = min(beta, score)
            if beta <= alpha:
                break
        return best


_DIFFICULTIES: dict[str, type[RandomStrategy | GreedyStrategy | MinimaxStrategy]] = {
    "easy": RandomStrategy,
    "medium": GreedyStrategy,
    "hard": MinimaxStrategy,
}


def get(difficulty: str) -> Strategy:
    try:
        return _DIFFICULTIES[difficulty]()
    except KeyError:
        raise ValueError(
            f"unknown difficulty {difficulty!r}; available: {', '.join(available())}"
        ) from None


def available() -> tuple[str, ...]:
    """Difficulty names, easiest first."""
    return tuple(_DIFFICULTIES)
