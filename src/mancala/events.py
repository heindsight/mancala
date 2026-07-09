"""Events narrate what happened during a move, in order, for consumers to replay."""

from dataclasses import dataclass

from mancala.state import Player


@dataclass(frozen=True, slots=True)
class SeedSown:
    """One seed dropped into `player`'s cup `cup`."""

    player: Player
    cup: int


@dataclass(frozen=True, slots=True)
class SeedStored:
    """One seed dropped into `player`'s store."""

    player: Player


@dataclass(frozen=True, slots=True)
class Captured:
    """`by` captured `seeds` seeds from `owner`'s cup `cup` into `by`'s store."""

    by: Player
    owner: Player
    cup: int
    seeds: int


@dataclass(frozen=True, slots=True)
class ExtraTurn:
    """`player` moves again."""

    player: Player


@dataclass(frozen=True, slots=True)
class GameOver:
    """The game ended; `winner` is None for a draw."""

    winner: Player | None


type Event = SeedSown | SeedStored | Captured | ExtraTurn | GameOver
