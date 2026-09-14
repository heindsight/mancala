"""Kalah: the classic store-and-capture mancala variant."""

from collections.abc import Container
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from mancala.engine.events import (
    Captured,
    Event,
    ExtraTurn,
    GameOver,
    SeedSown,
    SeedStored,
)
from mancala.engine.rules import Move, MoveResult
from mancala.engine.state import GameState, Player
from mancala.engine.variants._common import (
    board_empty,
    frozen,
    mutable,
    sweep_remaining,
    winner_from_stores,
)
from mancala.engine.variants.descriptor import VariantDescriptor

_CUPS = 6

# Sowing cycle: positions 0-5 are the mover's cups, 6 the mover's store,
# 7-12 the opponent's cups. The opponent's store is not part of the cycle.
_CYCLE = 2 * _CUPS + 1
_STORE = _CUPS


class KalahConfig(BaseModel):
    """Settings for one game of Kalah."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seeds_per_cup: Annotated[
        int,
        Field(
            ge=3,
            le=6,
            title="Seeds per cup",
            description="How many seeds each cup holds when the game starts.",
        ),
    ] = 4


class Kalah:
    def __init__(self, config: KalahConfig) -> None:
        self._config = config

    @property
    def config(self) -> KalahConfig:
        return self._config

    def initial_state(self) -> GameState:
        row = (self._config.seeds_per_cup,) * _CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        own = state.board[state.current_player.value]
        return tuple(cup for cup, seeds in enumerate(own) if seeds)

    def apply_move(
        self,
        state: GameState,
        move: Move,
        history: Container[GameState] = frozenset(),
    ) -> MoveResult:
        del history  # kalah has no repetition rule
        mover = state.current_player
        opponent = mover.opponent
        board, stores = mutable(state)
        events: list[Event] = []

        seeds = board[mover.value][move]
        board[mover.value][move] = 0
        pos = move
        while seeds:
            pos = (pos + 1) % _CYCLE
            if pos == _STORE:
                stores[mover.value] += 1
                events.append(SeedStored(mover))
            else:
                owner, cup = (
                    (mover, pos) if pos < _CUPS else (opponent, pos - _CUPS - 1)
                )
                board[owner.value][cup] += 1
                events.append(SeedSown(owner, cup))
            seeds -= 1

        opposite = _CUPS - 1 - pos
        if (
            pos < _CUPS
            and board[mover.value][pos] == 1
            and board[opponent.value][opposite]
        ):
            for owner, cup in ((mover, pos), (opponent, opposite)):
                taken = board[owner.value][cup]
                stores[mover.value] += taken
                board[owner.value][cup] = 0
                events.append(Captured(by=mover, owner=owner, cup=cup, seeds=taken))

        if not any(board[0]) or not any(board[1]):
            events.extend(sweep_remaining(board, stores))
            final = frozen(board, stores, opponent)
            events.append(GameOver(winner_from_stores(final)))
            return MoveResult(final, tuple(events))

        if pos == _STORE:
            events.append(ExtraTurn(mover))
            return MoveResult(frozen(board, stores, mover), tuple(events))

        return MoveResult(frozen(board, stores, opponent), tuple(events))

    def is_over(self, state: GameState) -> bool:
        return board_empty(state)

    def winner(self, state: GameState) -> Player | None:
        return winner_from_stores(state) if self.is_over(state) else None


DESCRIPTOR = VariantDescriptor(
    id="kalah", display_name="Kalah", config_model=KalahConfig, factory=Kalah
)
