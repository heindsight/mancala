"""Kalah: the classic store-and-capture mancala variant."""

from collections.abc import Container

from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.rules import Move, MoveResult
from mancala.state import GameState, Player
from mancala.variants._common import (
    CUPS,
    board_empty,
    frozen,
    mutable,
    sweep_remaining,
    winner_from_stores,
)

# Sowing cycle: positions 0-5 are the mover's cups, 6 the mover's store,
# 7-12 the opponent's cups. The opponent's store is not part of the cycle.
_CYCLE = 13
_STORE = CUPS


class Kalah:
    name = "kalah"

    def initial_state(self, seeds_per_cup: int = 4) -> GameState:
        if not 3 <= seeds_per_cup <= 6:
            raise ValueError("kalah supports 3-6 seeds per cup")
        row = (seeds_per_cup,) * CUPS
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
                owner, cup = (mover, pos) if pos < CUPS else (opponent, pos - CUPS - 1)
                board[owner.value][cup] += 1
                events.append(SeedSown(owner, cup))
            seeds -= 1

        opposite = CUPS - 1 - pos
        if (
            pos < CUPS
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
