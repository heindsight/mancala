import pytest
from helpers import make_state

from mancala.state import Player
from mancala.variants.kalah import Kalah

KALAH = Kalah()


def test_initial_state_has_four_seeds_per_cup_by_default() -> None:
    state = KALAH.initial_state()
    assert state.board == ((4,) * 6, (4,) * 6)
    assert state.stores == (0, 0)
    assert state.current_player is Player.SOUTH


def test_initial_state_accepts_three_to_six_seeds() -> None:
    assert KALAH.initial_state(seeds_per_cup=3).board == ((3,) * 6, (3,) * 6)
    assert KALAH.initial_state(seeds_per_cup=6).board == ((6,) * 6, (6,) * 6)


@pytest.mark.parametrize("seeds", [0, 1, 2, 7, -1])
def test_initial_state_rejects_unsupported_seed_counts(seeds: int) -> None:
    with pytest.raises(ValueError, match="3-6"):
        KALAH.initial_state(seeds_per_cup=seeds)


def test_legal_moves_are_the_movers_nonempty_cups() -> None:
    state = make_state(south=(0, 3, 0, 1, 0, 2), north=(4, 4, 4, 4, 4, 4))
    assert KALAH.legal_moves(state) == (1, 3, 5)


def test_legal_moves_use_the_current_players_row() -> None:
    state = make_state(south=(1, 1, 1, 1, 1, 1), north=(0, 0, 5, 0, 0, 0), player=Player.NORTH)
    assert KALAH.legal_moves(state) == (2,)
