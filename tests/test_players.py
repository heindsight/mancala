import random

import pytest
from helpers import make_state

from mancala import players
from mancala.players import GreedyPlayer, MinimaxPlayer, RandomPlayer
from mancala.variants.kalah import Kalah
from mancala.variants.oware import Oware

KALAH = Kalah()
OWARE = Oware()
OPENING = KALAH.initial_state()

# South can bait a capture of 3 with cup 1 (leaving the 6-pile in cup 3 to be
# captured back for 7), or defend by sowing the pile itself for a gain of 1.
TRAP = make_state(south=(1, 0, 6, 0, 0, 0), north=(0, 0, 1, 0, 2, 0))

SEEDS = range(20)


def trap_choices(strategy: type, *args: int) -> set[int]:
    """Moves chosen from TRAP by `strategy` over a spread of RNG seeds."""
    return {
        strategy(*args, rng=random.Random(seed)).choose(KALAH, TRAP) for seed in SEEDS
    }


def test_random_player_plays_a_legal_move() -> None:
    state = make_state(south=(1, 0, 0, 4, 0, 2), north=(4,) * 6)
    for seed in SEEDS:
        assert RandomPlayer(random.Random(seed)).choose(KALAH, state) in (0, 3, 5)


def test_random_player_varies_its_choice() -> None:
    assert trap_choices(RandomPlayer) == {0, 2}


def test_random_player_builds_its_own_rng_when_none_is_given() -> None:
    assert RandomPlayer().choose(KALAH, OPENING) in range(6)


def test_greedy_player_banks_the_most_seeds() -> None:
    # Cup 4 captures 1 + 4 seeds; cup 6 banks only 1.
    state = make_state(south=(0, 0, 0, 1, 0, 2), north=(4,) * 6)
    assert GreedyPlayer(random.Random(0)).choose(KALAH, state) == 3


def test_greedy_player_takes_the_bait_that_minimax_refuses() -> None:
    assert trap_choices(GreedyPlayer) == {0}


def test_greedy_player_breaks_ties_randomly() -> None:
    # North is out of seeds: either move ends the game and sweeps both south
    # seeds into its store, so the gains are equal and the tie is random.
    state = make_state(south=(1, 1, 0, 0, 0, 0), north=(0,) * 6)
    chosen = {GreedyPlayer(random.Random(seed)).choose(KALAH, state) for seed in SEEDS}
    assert chosen == {0, 1}


def test_greedy_player_builds_its_own_rng_when_none_is_given() -> None:
    assert GreedyPlayer().choose(KALAH, OPENING) in range(6)


def test_minimax_player_defends_instead_of_baiting_a_bigger_counter_capture() -> None:
    assert trap_choices(MinimaxPlayer, 4) == {2}


def test_minimax_player_scores_finished_games_by_their_final_margin() -> None:
    # North is out of seeds, so either move ends the game and sweeps south's
    # row into its store: the outcomes are identical and the tie is random.
    state = make_state(south=(0, 0, 0, 0, 1, 1), north=(0,) * 6, stores=(20, 26))
    chosen = {
        MinimaxPlayer(rng=random.Random(seed)).choose(KALAH, state) for seed in SEEDS
    }
    assert chosen == {4, 5}


def test_minimax_player_plays_a_legal_move_from_the_kalah_opening() -> None:
    assert MinimaxPlayer(depth=4, rng=random.Random(0)).choose(
        KALAH, OPENING
    ) in KALAH.legal_moves(OPENING)


def test_minimax_player_plays_a_legal_move_from_the_oware_opening() -> None:
    opening = OWARE.initial_state()
    assert MinimaxPlayer(depth=4, rng=random.Random(0)).choose(
        OWARE, opening
    ) in OWARE.legal_moves(opening)


def test_minimax_player_builds_its_own_rng_when_none_is_given() -> None:
    assert MinimaxPlayer(depth=2).choose(KALAH, OPENING) in range(6)


def test_available_lists_the_difficulties_easiest_first() -> None:
    assert players.available() == ("easy", "medium", "hard")


@pytest.mark.parametrize(
    ("difficulty", "cls"),
    [("easy", RandomPlayer), ("medium", GreedyPlayer), ("hard", MinimaxPlayer)],
)
def test_get_builds_the_strategy_for_each_difficulty(
    difficulty: str, cls: type
) -> None:
    assert isinstance(players.get(difficulty), cls)


def test_get_rejects_unknown_difficulties_and_lists_the_available_ones() -> None:
    with pytest.raises(ValueError, match="unknown difficulty 'expert'") as excinfo:
        players.get("expert")
    assert str(excinfo.value) == (
        "unknown difficulty 'expert'; available: easy, medium, hard"
    )
