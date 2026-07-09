import pytest
from helpers import make_state

from mancala.state import Player
from mancala.variants.oware import Oware

OWARE = Oware()


def test_initial_state_is_six_cups_of_four() -> None:
    state = OWARE.initial_state()
    assert state.board == ((4,) * 6, (4,) * 6)
    assert state.stores == (0, 0)
    assert state.current_player is Player.SOUTH


@pytest.mark.parametrize("seeds", [3, 5, 6])
def test_initial_state_rejects_anything_but_four_seeds(seeds: int) -> None:
    with pytest.raises(ValueError, match="4 seeds"):
        OWARE.initial_state(seeds_per_cup=seeds)


def test_legal_moves_are_the_movers_nonempty_cups() -> None:
    state = make_state(south=(0, 2, 0, 0, 1, 0), north=(4, 4, 4, 4, 4, 4))
    assert OWARE.legal_moves(state) == (1, 4)


def test_starved_opponent_restricts_moves_to_feeding_ones() -> None:
    # North is empty: south cup 0 (1 seed reaches cup 1 only) cannot feed;
    # cup 5 (3 seeds reach north cups 0-2) can.
    state = make_state(south=(1, 0, 0, 0, 0, 3), north=(0,) * 6)
    assert OWARE.legal_moves(state) == (5,)


def test_no_legal_moves_when_starved_opponent_cannot_be_fed() -> None:
    state = make_state(south=(1, 1, 0, 0, 0, 0), north=(0,) * 6)
    assert OWARE.legal_moves(state) == ()
