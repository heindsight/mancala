import random

import pytest
from helpers import make_state

from mancala import players
from mancala.players import GreedyPlayer, MinimaxPlayer, RandomPlayer
from mancala.state import GameState, Player
from mancala.variants.kalah import Kalah
from mancala.variants.oware import Oware

KALAH = Kalah()
OWARE = Oware()
OPENING = KALAH.initial_state()

# South can bait a capture of 3 with cup 1 (leaving the 6-pile in cup 3 to be
# captured back for 7), or defend by sowing the pile itself for a gain of 1.
TRAP = make_state(south=(1, 0, 6, 0, 0, 0), north=(0, 0, 1, 0, 2, 0))

# Cup 6 banks a seed and earns an extra turn; the follow-up from cup 5 then
# captures North's last seed and sweeps the board for a 4-0 win. Only a search
# that keeps South as the maximiser on that second move sees the win; keyed on
# ply parity it counts the follow-up as the opponent's choice and prefers cup 5
# immediately.
EXTRA_TURN = make_state(south=(0, 0, 1, 0, 1, 1), north=(1, 0, 0, 0, 0, 0))

# Any south move here ends the game and sweeps south's row into its store.
NEAR_END = make_state(south=(0, 0, 0, 0, 1, 1), north=(0,) * 6, stores=(20, 26))

# In oware, sowing cup 6 recreates the position in REPETITION_SEEN, which ends
# the game by repetition: the sweep banks South's remaining seed for 22-26.
# Without the history both moves look equally barren.
REPETITION = make_state(
    south=(0, 0, 1, 0, 0, 1), north=(0, 1, 0, 0, 0, 1), stores=(21, 23)
)
REPETITION_SEEN = frozenset(
    {
        make_state(
            south=(0, 0, 1, 0, 0, 0),
            north=(1, 1, 0, 0, 0, 1),
            stores=(21, 23),
            player=Player.NORTH,
        )
    }
)

SEEDS = range(20)


def trap_choices(strategy: type, *args: int) -> set[int]:
    """Moves chosen from TRAP by `strategy` over a spread of RNG seeds."""
    return {
        strategy(*args, rng=random.Random(seed)).choose(KALAH, TRAP) for seed in SEEDS
    }


def random_kalah_position(moves: int, rng: random.Random) -> GameState:
    state = KALAH.initial_state()
    for _ in range(moves):
        state = KALAH.apply_move(state, rng.choice(KALAH.legal_moves(state))).state
    return state


def reference_values(state: GameState, depth: int) -> dict[int, tuple[float, float]]:
    """Each root move's plain minimax value, scored like MinimaxPlayer."""
    me = state.current_player

    def value(state: GameState, depth: int) -> tuple[float, float]:
        margin = state.stores[me.value] - state.stores[me.opponent.value]
        if KALAH.is_over(state):
            return ((margin > 0) - (margin < 0), margin)
        if depth == 0:
            return (0, margin)
        children = [
            value(KALAH.apply_move(state, move).state, depth - 1)
            for move in KALAH.legal_moves(state)
        ]
        return max(children) if state.current_player is me else min(children)

    return {
        move: value(KALAH.apply_move(state, move).state, depth - 1)
        for move in KALAH.legal_moves(state)
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


def test_greedy_player_banks_the_sweep_from_a_repetition_ending() -> None:
    chosen = {
        GreedyPlayer(random.Random(seed)).choose(OWARE, REPETITION, REPETITION_SEEN)
        for seed in SEEDS
    }
    assert chosen == {5}


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


def test_minimax_player_keeps_maximising_through_an_extra_turn() -> None:
    chosen = {
        MinimaxPlayer(depth=3, rng=random.Random(seed)).choose(KALAH, EXTRA_TURN)
        for seed in SEEDS
    }
    assert chosen == {5}


def test_minimax_player_avoids_a_losing_repetition_ending() -> None:
    chosen = {
        MinimaxPlayer(depth=1, rng=random.Random(seed)).choose(
            OWARE, REPETITION, REPETITION_SEEN
        )
        for seed in SEEDS
    }
    assert chosen == {2}


@pytest.mark.parametrize(
    "state",
    [
        TRAP,
        EXTRA_TURN,
        NEAR_END,
        *(random_kalah_position(2 * n, random.Random(n)) for n in range(8)),
    ],
)
def test_minimax_player_agrees_with_an_unpruned_reference_search(
    state: GameState,
) -> None:
    values = reference_values(state, depth=3)
    choice = MinimaxPlayer(depth=3, rng=random.Random(0)).choose(KALAH, state)
    assert values[choice] == max(values.values())


@pytest.mark.parametrize("depth", [0, -1])
def test_minimax_player_rejects_a_depth_below_one(depth: int) -> None:
    with pytest.raises(ValueError, match="depth must be at least 1"):
        MinimaxPlayer(depth=depth)


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
