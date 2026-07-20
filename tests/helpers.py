"""Shared test helpers."""

from hypothesis import assume
from hypothesis import strategies as st

from mancala import variants
from mancala.match import Match
from mancala.state import GameState, Player


def make_state(
    south: tuple[int, ...],
    north: tuple[int, ...],
    stores: tuple[int, int] = (0, 0),
    player: Player = Player.SOUTH,
) -> GameState:
    return GameState(board=(south, north), stores=stores, current_player=player)


@st.composite
def matches(
    draw: st.DrawFn, names: tuple[str, ...] = ("kalah", "oware"), plies: int = 10
) -> Match:
    """A match still in play, advanced from the opening by up to `plies` legal moves."""
    rules = variants.get(draw(st.sampled_from(names)))
    match = Match(rules, rules.initial_state())
    target = draw(st.integers(min_value=0, max_value=plies))
    while len(match.history) < target and not match.is_over:
        match.play(draw(st.sampled_from(rules.legal_moves(match.state))))
    assume(not match.is_over)
    return match
