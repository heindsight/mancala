import re

import pytest
from helpers import make_state

from mancala.events import SeedSown
from mancala.match import Match
from mancala.rules import IllegalMoveError
from mancala.state import Player
from mancala.variants.kalah import Kalah

KALAH = Kalah()


def test_match_starts_from_the_initial_state_by_default() -> None:
    match = Match(KALAH)
    assert match.state == KALAH.initial_state()
    assert match.history == ()
    assert not match.is_over
    assert match.winner is None


def test_play_advances_the_state_and_records_history() -> None:
    match = Match(KALAH)
    before = match.state
    result = match.play(0)  # south sows its four leftmost seeds, passing the turn
    expected = make_state(
        south=(0, 5, 5, 5, 5, 4), north=(4, 4, 4, 4, 4, 4), player=Player.NORTH
    )
    assert result.state == expected
    assert result.events == (
        SeedSown(Player.SOUTH, 1),
        SeedSown(Player.SOUTH, 2),
        SeedSown(Player.SOUTH, 3),
        SeedSown(Player.SOUTH, 4),
    )
    assert match.state == result.state
    assert match.history == ((before, 0, result.events),)


def test_playing_an_empty_cup_is_illegal() -> None:
    match = Match(KALAH, make_state(south=(0, 4, 0, 0, 0, 0), north=(1, 1, 1, 1, 1, 1)))
    with pytest.raises(IllegalMoveError, match="cup 1"):
        match.play(0)


@pytest.mark.parametrize(
    ("move", "message"),
    [
        (-1, "cup 0 is not a legal move"),
        (6, "cup 7 is not a legal move"),
        (99, "cup 100 is not a legal move"),
    ],
)
def test_out_of_range_moves_are_illegal(move: int, message: str) -> None:
    match = Match(KALAH)
    with pytest.raises(IllegalMoveError, match=rf"^{re.escape(message)}$"):
        match.play(move)


def test_playing_after_the_game_is_over_is_illegal() -> None:
    match = Match(KALAH, make_state(south=(0,) * 6, north=(0,) * 6, stores=(25, 23)))
    assert match.is_over
    assert match.winner is Player.SOUTH
    with pytest.raises(IllegalMoveError, match="over"):
        match.play(0)


def test_an_illegal_move_leaves_the_match_unchanged() -> None:
    match = Match(KALAH)
    before = match.state
    with pytest.raises(IllegalMoveError):
        match.play(-1)
    assert match.state == before
    assert match.history == ()


def test_unresolved_states_are_rejected() -> None:
    # South's row is empty but was never swept: no legal moves, yet not
    # "over". apply_move never produces such states; reject them up front.
    unswept = make_state(south=(0,) * 6, north=(1, 1, 1, 1, 1, 1), stores=(20, 22))
    with pytest.raises(ValueError, match="unresolved"):
        Match(KALAH, unswept)
