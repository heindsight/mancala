"""Oware (Abapa rules): capture-by-twos-and-threes mancala."""

from collections.abc import Container

from mancala.engine.events import Captured, Event, GameOver, SeedSown
from mancala.engine.rules import Move, MoveResult
from mancala.engine.state import GameState, Player
from mancala.engine.variants._common import (
    board_empty,
    frozen,
    mutable,
    sweep_remaining,
    winner_from_stores,
)

_CUPS = 6
_SEEDS_PER_CUP = 4

# Sowing cycle: positions 0-5 are the mover's cups, 6-11 the opponent's.
_CYCLE = 2 * _CUPS

_TOTAL_SEEDS = 2 * _CUPS * _SEEDS_PER_CUP
_TARGET = _TOTAL_SEEDS // 2  # capturing more than half of the seeds wins


class Oware:
    name = "oware"
    SEED_COUNTS = (_SEEDS_PER_CUP,)

    def initial_state(self, seeds_per_cup: int = _SEEDS_PER_CUP) -> GameState:
        if seeds_per_cup not in self.SEED_COUNTS:
            raise ValueError(
                f"oware is played with exactly {_SEEDS_PER_CUP} seeds per cup"
            )
        row = (seeds_per_cup,) * _CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        mover = state.current_player
        own = state.board[mover.value]
        moves = tuple(cup for cup, seeds in enumerate(own) if seeds)
        if any(state.board[mover.opponent.value]):
            return moves
        # Opponent is out of seeds: only a move that reaches their row feeds them.
        return tuple(cup for cup in moves if cup + own[cup] >= _CUPS)

    def apply_move(
        self,
        state: GameState,
        move: Move,
        history: Container[GameState] = frozenset(),
    ) -> MoveResult:
        mover = state.current_player
        opponent = mover.opponent
        board, stores = mutable(state)
        events: list[Event] = []

        seeds = board[mover.value][move]
        board[mover.value][move] = 0
        pos = move
        while seeds:
            pos = (pos + 1) % _CYCLE
            if pos == move:  # the origin cup is never resown
                continue
            owner, cup = (mover, pos) if pos < _CUPS else (opponent, pos - _CUPS)
            board[owner.value][cup] += 1
            events.append(SeedSown(owner, cup))
            seeds -= 1

        if pos >= _CUPS:  # landed in the opponent's row: try to capture
            chain: list[int] = []
            p = pos
            while p >= _CUPS and board[opponent.value][p - _CUPS] in (2, 3):
                chain.append(p - _CUPS)
                p -= 1
            taking = sum(board[opponent.value][cup] for cup in chain)
            if chain and taking < sum(board[opponent.value]):  # grand slam forfeits
                for cup in chain:
                    taken = board[opponent.value][cup]
                    stores[mover.value] += taken
                    board[opponent.value][cup] = 0
                    events.append(
                        Captured(by=mover, owner=opponent, cup=cup, seeds=taken)
                    )

        candidate = frozen(board, stores, opponent)
        game_over = (
            stores[mover.value] > _TARGET
            or not self.legal_moves(candidate)
            or candidate in history
        )
        if game_over:
            events.extend(sweep_remaining(board, stores))
            final = frozen(board, stores, opponent)
            events.append(GameOver(winner_from_stores(final)))
            return MoveResult(final, tuple(events))

        return MoveResult(candidate, tuple(events))

    def is_over(self, state: GameState) -> bool:
        return board_empty(state)

    def winner(self, state: GameState) -> Player | None:
        return winner_from_stores(state) if self.is_over(state) else None
