"""Shared test helpers."""

from mancala.state import GameState, Player


def make_state(
    south: tuple[int, ...],
    north: tuple[int, ...],
    stores: tuple[int, int] = (0, 0),
    player: Player = Player.SOUTH,
) -> GameState:
    return GameState(board=(south, north), stores=stores, current_player=player)
