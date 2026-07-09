"""Helpers shared by variant implementations (internal)."""

from mancala.events import Captured, Event
from mancala.state import GameState, Player

CUPS = 6


def mutable(state: GameState) -> tuple[list[list[int]], list[int]]:
    """Working copies of the board and stores for building the next state."""
    return [list(row) for row in state.board], list(state.stores)


def frozen(board: list[list[int]], stores: list[int], player: Player) -> GameState:
    return GameState(
        board=(tuple(board[0]), tuple(board[1])),
        stores=(stores[0], stores[1]),
        current_player=player,
    )


def sweep_remaining(board: list[list[int]], stores: list[int]) -> list[Event]:
    """Move every seed left on each side to its owner's store."""
    events: list[Event] = []
    for player in Player:
        for cup, seeds in enumerate(board[player.value]):
            if seeds:
                stores[player.value] += seeds
                board[player.value][cup] = 0
                events.append(Captured(by=player, owner=player, cup=cup, seeds=seeds))
    return events


def board_empty(state: GameState) -> bool:
    return not any(state.board[0]) and not any(state.board[1])


def winner_from_stores(state: GameState) -> Player | None:
    south, north = state.stores
    if south > north:
        return Player.SOUTH
    if north > south:
        return Player.NORTH
    return None
