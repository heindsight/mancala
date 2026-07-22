from collections.abc import Sequence

import pytest
from helpers import make_state, matches
from hypothesis import given

from mancala import strategies
from mancala.match import Match
from mancala.rules import Move, Rules
from mancala.state import GameState, Player
from mancala.strategies import GreedyStrategy, MinimaxStrategy, RandomStrategy
from mancala.variants.kalah import Kalah

KALAH = Kalah()


class FirstChoice:
    """A stand-in RNG that records what it was offered and always picks the first."""

    def __init__(self) -> None:
        self.offered: list[tuple[object, ...]] = []

    def choice[T](self, seq: Sequence[T]) -> T:
        self.offered.append(tuple(seq))
        return seq[0]


def kalah_match(
    south: tuple[int, ...], north: tuple[int, ...], stores: tuple[int, int] = (0, 0)
) -> Match:
    return Match(KALAH, make_state(south=south, north=north, stores=stores))


def reference_value(
    rules: Rules,
    me: Player,
    state: GameState,
    history: frozenset[GameState],
    depth: int,
) -> tuple[float, float]:
    """Full-width minimax, scored the way MinimaxStrategy scores but without pruning."""
    margin = state.stores[me.value] - state.stores[me.opponent.value]
    if rules.is_over(state):
        return ((margin > 0) - (margin < 0), margin)
    if depth == 0:
        return (0, margin)
    children = []
    for move in rules.legal_moves(state):
        after = rules.apply_move(state, move, history).state
        children.append(reference_value(rules, me, after, history | {after}, depth - 1))
    return max(children) if state.current_player is me else min(children)


def reference_best_moves(match: Match, depth: int) -> set[Move]:
    """Every root move a full-width search of `depth` plies rates joint best."""
    me = match.state.current_player
    values = {}
    for move in match.rules.legal_moves(match.state):
        after = match.rules.apply_move(match.state, move, match.seen).state
        values[move] = reference_value(
            match.rules, me, after, match.seen | {after}, depth - 1
        )
    best = max(values.values())
    return {move for move, value in values.items() if value == best}


@pytest.fixture
def trap() -> Match:
    """South can capture 3 now, but that leaves a 6-pile to be captured back for 7."""
    return kalah_match(south=(1, 0, 6, 0, 0, 0), north=(0, 0, 1, 0, 2, 0))


@pytest.fixture
def extra_turn() -> Match:
    """South's cup 6 banks a seed and earns a follow-up from cup 5 that wins 4-0."""
    return kalah_match(south=(0, 0, 1, 0, 1, 1), north=(1, 0, 0, 0, 0, 0))


@pytest.fixture
def winning_capture() -> Match:
    """South's cup 4 takes North's last seeds and ends the game 25-23; cup 6 banks 1."""
    return kalah_match(
        south=(0, 0, 0, 1, 0, 2), north=(0, 3, 0, 0, 0, 0), stores=(19, 23)
    )


def test_random_strategy_chooses_between_all_the_legal_moves() -> None:
    rng = FirstChoice()
    RandomStrategy(rng).choose(kalah_match(south=(1, 0, 0, 4, 0, 2), north=(4,) * 6))
    assert rng.offered == [(0, 3, 5)]


@given(match=matches())
def test_random_strategy_plays_a_legal_move(match: Match) -> None:
    assert RandomStrategy().choose(match) in match.rules.legal_moves(match.state)


def test_greedy_strategy_prefers_a_capture_to_a_smaller_bank() -> None:
    match = kalah_match(south=(0, 0, 0, 1, 0, 2), north=(4,) * 6)
    assert GreedyStrategy(FirstChoice()).choose(match) == 3


def test_greedy_strategy_takes_the_bait_that_minimax_refuses(trap: Match) -> None:
    assert GreedyStrategy(FirstChoice()).choose(trap) == 0


def test_greedy_strategy_chooses_between_the_moves_that_bank_equally() -> None:
    rng = FirstChoice()
    GreedyStrategy(rng).choose(kalah_match(south=(1, 1, 0, 0, 0, 0), north=(0,) * 6))
    assert rng.offered == [(0, 1)]


@given(match=matches())
def test_greedy_strategy_plays_a_legal_move(match: Match) -> None:
    assert GreedyStrategy().choose(match) in match.rules.legal_moves(match.state)


def test_minimax_strategy_defends_instead_of_baiting_a_bigger_counter_capture(
    trap: Match,
) -> None:
    assert MinimaxStrategy(depth=4, rng=FirstChoice()).choose(trap) == 2


def test_minimax_strategy_keeps_maximising_through_an_extra_turn(
    extra_turn: Match,
) -> None:
    assert MinimaxStrategy(depth=3, rng=FirstChoice()).choose(extra_turn) == 5


def test_minimax_strategy_plays_the_move_that_ends_the_game_in_a_win(
    winning_capture: Match,
) -> None:
    assert MinimaxStrategy(depth=2, rng=FirstChoice()).choose(winning_capture) == 3


def test_minimax_strategy_chooses_between_endings_of_equal_margin() -> None:
    rng = FirstChoice()
    match = kalah_match(south=(0, 0, 0, 0, 1, 1), north=(0,) * 6, stores=(20, 26))
    MinimaxStrategy(rng=rng).choose(match)
    assert rng.offered == [(4, 5)]


@given(match=matches())
def test_minimax_strategy_agrees_with_a_search_that_does_not_prune(
    match: Match,
) -> None:
    chosen = MinimaxStrategy(depth=3, rng=FirstChoice()).choose(match)
    assert chosen in reference_best_moves(match, depth=3)


def test_minimax_strategy_agrees_with_an_unpruned_search_through_the_endgame(
    winning_capture: Match,
) -> None:
    chosen = MinimaxStrategy(depth=3, rng=FirstChoice()).choose(winning_capture)
    assert chosen in reference_best_moves(winning_capture, depth=3)


@given(match=matches())
def test_minimax_strategy_plays_a_legal_move(match: Match) -> None:
    assert MinimaxStrategy(depth=3).choose(match) in match.rules.legal_moves(
        match.state
    )


@pytest.mark.parametrize("depth", [0, -1])
def test_minimax_strategy_rejects_a_depth_below_one(depth: int) -> None:
    with pytest.raises(ValueError, match="depth must be at least 1"):
        MinimaxStrategy(depth=depth)


def test_available_lists_the_difficulties_easiest_first() -> None:
    assert strategies.available() == ("easy", "medium", "hard")


@pytest.mark.parametrize(
    ("difficulty", "expected"),
    [("easy", RandomStrategy), ("medium", GreedyStrategy), ("hard", MinimaxStrategy)],
)
def test_get_builds_the_strategy_for_each_difficulty(
    difficulty: str, expected: type
) -> None:
    assert isinstance(strategies.get(difficulty), expected)


def test_get_rejects_unknown_difficulties_and_lists_the_available_ones() -> None:
    with pytest.raises(ValueError, match="unknown difficulty") as excinfo:
        strategies.get("expert")
    assert str(excinfo.value) == (
        "unknown difficulty 'expert'; available: easy, medium, hard"
    )
