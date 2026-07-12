import dataclasses

import pytest

from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.rules import IllegalMoveError, MoveResult
from mancala.state import GameState, Player


def test_same_shaped_events_of_different_types_are_not_equal() -> None:
    # This is why events are frozen dataclasses rather than NamedTuples.
    assert SeedStored(Player.SOUTH) != ExtraTurn(Player.SOUTH)
    assert GameOver(Player.SOUTH) != ExtraTurn(Player.SOUTH)


def test_events_are_value_equal_within_a_type() -> None:
    assert SeedSown(Player.NORTH, 3) == SeedSown(Player.NORTH, 3)
    assert Captured(by=Player.SOUTH, owner=Player.NORTH, cup=2, seeds=3) == Captured(
        by=Player.SOUTH, owner=Player.NORTH, cup=2, seeds=3
    )


def test_events_are_immutable() -> None:
    event = SeedSown(Player.SOUTH, 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.cup = 5  # ty: ignore[invalid-assignment]


def test_move_result_carries_state_and_events() -> None:
    state = GameState(
        board=((0,) * 6, (0,) * 6), stores=(24, 24), current_player=Player.SOUTH
    )
    result = MoveResult(state=state, events=(GameOver(None),))
    assert result.state is state
    assert result.events == (GameOver(None),)


def test_illegal_move_error_is_an_exception() -> None:
    assert issubclass(IllegalMoveError, Exception)
