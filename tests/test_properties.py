from hypothesis import given, settings
from hypothesis import strategies as st

from mancala import variants
from mancala.events import Captured, SeedSown
from mancala.match import Match
from mancala.state import Player


@settings(deadline=None)
@given(
    name=st.sampled_from(["kalah", "oware"]),
    seeds_per_cup=st.sampled_from([3, 4, 5, 6]),
    data=st.data(),
)
def test_random_playout_invariants(name: str, seeds_per_cup: int, data: st.DataObject) -> None:
    rules = variants.get(name)
    if name != "kalah":
        seeds_per_cup = 4
    match = Match(rules, rules.initial_state(seeds_per_cup))
    total = 2 * 6 * seeds_per_cup

    for _ in range(200):
        if match.is_over:
            break
        moves = rules.legal_moves(match.state)
        assert moves, "a non-terminal state must have legal moves"
        result = match.play(data.draw(st.sampled_from(moves)))

        state = result.state
        assert all(seeds >= 0 for row in state.board for seeds in row)
        assert sum(state.stores) + sum(sum(row) for row in state.board) == total
        for event in result.events:
            if isinstance(event, SeedSown | Captured):
                assert 0 <= event.cup < 6

    if match.is_over:
        assert rules.legal_moves(match.state) == ()
        assert match.state.board == ((0,) * 6, (0,) * 6)
        assert sum(match.state.stores) == total
        south, north = match.state.stores
        expected = None if south == north else Player.SOUTH if south > north else Player.NORTH
        assert match.winner is expected
