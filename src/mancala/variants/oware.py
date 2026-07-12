"""Oware (Abapa rules): capture-by-twos-and-threes mancala."""

from collections.abc import Container

from mancala.events import Captured, Event, GameOver, SeedSown
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

# Sowing cycle: positions 0-5 are the mover's cups, 6-11 the opponent's.
_CYCLE = 2 * CUPS

_TARGET = 24  # capturing more than half of the 48 seeds wins


class Oware:
    name = "oware"

    def initial_state(self, seeds_per_cup: int = 4) -> GameState:
        if seeds_per_cup != 4:
            raise ValueError("oware is played with exactly 4 seeds per cup")
        row = (seeds_per_cup,) * CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        mover = state.current_player
        own = state.board[mover.value]
        moves = tuple(cup for cup, seeds in enumerate(own) if seeds)
        if any(state.board[mover.opponent.value]):
            return moves
        # Opponent is out of seeds: only a move that reaches their row feeds them.
        return tuple(cup for cup in moves if cup + own[cup] >= CUPS)

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
            owner, cup = (mover, pos) if pos < CUPS else (opponent, pos - CUPS)
            board[owner.value][cup] += 1
            events.append(SeedSown(owner, cup))
            seeds -= 1

        if pos >= CUPS:  # landed in the opponent's row: try to capture
            chain: list[int] = []
            p = pos
            while p >= CUPS and board[opponent.value][p - CUPS] in (2, 3):
                chain.append(p - CUPS)
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
