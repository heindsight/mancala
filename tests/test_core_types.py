import dataclasses

import pytest

from mancala.events import ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.state import Player


def test_same_shaped_events_of_different_types_are_not_equal() -> None:
    # This is why events are frozen dataclasses rather than NamedTuples.
    assert SeedStored(Player.SOUTH) != ExtraTurn(Player.SOUTH)
    assert GameOver(Player.SOUTH) != ExtraTurn(Player.SOUTH)


def test_events_are_immutable() -> None:
    event = SeedSown(Player.SOUTH, 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.cup = 5  # ty: ignore[invalid-assignment]
