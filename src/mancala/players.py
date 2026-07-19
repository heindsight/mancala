"""Computer players: move-selection strategies at three difficulty levels."""

import random
from collections.abc import Set
from math import inf
from typing import Protocol

from mancala.rules import Move, Rules
from mancala.state import GameState, Player


class Strategy(Protocol):
    """Chooses a legal move for the current player of a state.

    `history` holds the states already seen this game (`Match.seen`); it is
    threaded into `Rules.apply_move` so simulated moves resolve repetition
    endings exactly as the real match would.
    """

    def choose(
        self,
        rules: Rules,
        state: GameState,
        history: Set[GameState] = frozenset(),
    ) -> Move: ...


class RandomPlayer:
    """Easy: plays a uniformly random legal move."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def choose(
        self,
        rules: Rules,
        state: GameState,
        history: Set[GameState] = frozenset(),
    ) -> Move:
        del history  # legal moves don't depend on repetition history
        return self._rng.choice(rules.legal_moves(state))


class GreedyPlayer:
    """Medium: banks the most seeds this move; ties are broken randomly."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def choose(
        self,
        rules: Rules,
        state: GameState,
        history: Set[GameState] = frozenset(),
    ) -> Move:
        mover = state.current_player

        def gain(move: Move) -> int:
            after = rules.apply_move(state, move, history).state
            return after.stores[mover.value] - state.stores[mover.value]

        gains = {move: gain(move) for move in rules.legal_moves(state)}
        best = max(gains.values())
        return self._rng.choice([move for move, g in gains.items() if g == best])


# Scores are (outcome, margin) pairs: outcome is the sign of a finished game's
# margin and 0 for unfinished positions, so in any variant a guaranteed win
# outranks any heuristic lead (and bigger wins outrank smaller).
type _Score = tuple[float, float]

_MIN: _Score = (-inf, -inf)
_MAX: _Score = (inf, inf)


class MinimaxPlayer:
    """Hard: depth-limited minimax with alpha-beta pruning.

    Positions are scored by store difference, with finished games ranked
    above (won) or below (lost) every unfinished position. Extra turns are
    handled by switching between maximising and minimising on the state's
    actual mover rather than by ply parity, and the repetition history is
    extended along every simulated line. Root moves are searched with a full
    window so equally good moves score identically and ties can be broken
    randomly.
    """

    def __init__(self, depth: int = 6, rng: random.Random | None = None) -> None:
        if depth < 1:
            raise ValueError("depth must be at least 1")
        self._depth = depth
        self._rng = rng if rng is not None else random.Random()

    def choose(
        self,
        rules: Rules,
        state: GameState,
        history: Set[GameState] = frozenset(),
    ) -> Move:
        me = state.current_player

        def value(
            state: GameState,
            depth: int,
            alpha: _Score,
            beta: _Score,
            history: Set[GameState],
        ) -> _Score:
            if rules.is_over(state):
                margin = _margin(state, me)
                return ((margin > 0) - (margin < 0), margin)
            if depth == 0:
                return (0, _margin(state, me))
            maximising = state.current_player is me
            best = _MIN if maximising else _MAX
            for move in rules.legal_moves(state):
                after = rules.apply_move(state, move, history).state
                seen = value(after, depth - 1, alpha, beta, history | {after})
                if maximising:
                    best = max(best, seen)
                    alpha = max(alpha, seen)
                else:
                    best = min(best, seen)
                    beta = min(beta, seen)
                if beta <= alpha:
                    break
            return best

        def searched(move: Move) -> _Score:
            after = rules.apply_move(state, move, history).state
            return value(after, self._depth - 1, _MIN, _MAX, history | {after})

        values = {move: searched(move) for move in rules.legal_moves(state)}
        best = max(values.values())
        return self._rng.choice([move for move, v in values.items() if v == best])


def _margin(state: GameState, player: Player) -> int:
    return state.stores[player.value] - state.stores[player.opponent.value]


_DIFFICULTIES: dict[str, type[RandomPlayer | GreedyPlayer | MinimaxPlayer]] = {
    "easy": RandomPlayer,
    "medium": GreedyPlayer,
    "hard": MinimaxPlayer,
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
