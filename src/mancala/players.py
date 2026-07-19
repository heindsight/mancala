"""Computer players: move-selection strategies at three difficulty levels."""

import random
from math import inf
from typing import Protocol

from mancala.rules import Move, Rules
from mancala.state import GameState, Player


class Strategy(Protocol):
    """Chooses a legal move for the current player of a state."""

    def choose(self, rules: Rules, state: GameState) -> Move: ...


class RandomPlayer:
    """Easy: plays a uniformly random legal move."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def choose(self, rules: Rules, state: GameState) -> Move:
        return self._rng.choice(rules.legal_moves(state))


class GreedyPlayer:
    """Medium: banks the most seeds this move; ties are broken randomly."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def choose(self, rules: Rules, state: GameState) -> Move:
        mover = state.current_player

        def gain(move: Move) -> int:
            after = rules.apply_move(state, move).state
            return after.stores[mover.value] - state.stores[mover.value]

        gains = {move: gain(move) for move in rules.legal_moves(state)}
        best = max(gains.values())
        return self._rng.choice([move for move, g in gains.items() if g == best])


# Terminal margins are scaled by this so that any guaranteed win outranks any
# heuristic lead in an unfinished position (and bigger wins outrank smaller).
_WIN = 100


class MinimaxPlayer:
    """Hard: depth-limited minimax with alpha-beta pruning.

    Positions are scored by store difference. Extra turns are handled by
    switching between maximising and minimising on the state's actual mover
    rather than by ply parity. Root moves are searched with a full window so
    equally good moves score identically and ties can be broken randomly.
    """

    def __init__(self, depth: int = 6, rng: random.Random | None = None) -> None:
        self._depth = depth
        self._rng = rng if rng is not None else random.Random()

    def choose(self, rules: Rules, state: GameState) -> Move:
        me = state.current_player

        def value(state: GameState, depth: int, alpha: float, beta: float) -> float:
            if rules.is_over(state):
                return _WIN * _margin(state, me)
            if depth == 0:
                return _margin(state, me)
            maximising = state.current_player is me
            best = -inf if maximising else inf
            for move in rules.legal_moves(state):
                after = rules.apply_move(state, move).state
                seen = value(after, depth - 1, alpha, beta)
                if maximising:
                    best = max(best, seen)
                    alpha = max(alpha, seen)
                else:
                    best = min(best, seen)
                    beta = min(beta, seen)
                if beta <= alpha:
                    break
            return best

        values = {
            move: value(rules.apply_move(state, move).state, self._depth - 1, -inf, inf)
            for move in rules.legal_moves(state)
        }
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
