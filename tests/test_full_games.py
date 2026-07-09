from helpers import make_state

from mancala import variants
from mancala.events import GameOver
from mancala.match import Match
from mancala.state import Player


def test_scripted_kalah_endgame_plays_out_to_a_north_win() -> None:
    # Hand-verified script: south empties its row on the third move.
    start = make_state(south=(0, 0, 0, 0, 1, 2), north=(1, 0, 0, 0, 0, 1), stores=(20, 23))
    match = Match(variants.get("kalah"), start)

    match.play(4)  # south: 1 seed to cup 5 (now 3 seeds)
    assert match.state.board[Player.SOUTH.value] == (0, 0, 0, 0, 0, 3)
    assert not match.is_over

    match.play(0)  # north: 1 seed to own empty cup 1; opposite south cup 4 is empty -> no capture
    assert match.state.board[Player.NORTH.value] == (0, 1, 0, 0, 0, 1)
    assert match.state.stores == (20, 23)

    result = match.play(5)  # south: store, north cups 0-1; south's row is now empty
    assert match.is_over
    assert match.state.board == ((0,) * 6, (0,) * 6)
    assert match.state.stores == (21, 27)
    assert match.winner is Player.NORTH
    assert result.events[-1] == GameOver(Player.NORTH)


def first_legal_playout(name: str) -> Match:
    match = Match(variants.get(name))
    plies = 0
    while not match.is_over:
        match.play(match.rules.legal_moves(match.state)[0])
        plies += 1
        assert plies < 10_000, "playout did not terminate"
    return match


def test_kalah_first_legal_playout_terminates_and_conserves_seeds() -> None:
    match = first_legal_playout("kalah")
    assert sum(match.state.stores) == 48
    assert match.state.board == ((0,) * 6, (0,) * 6)


def test_oware_first_legal_playout_terminates_and_conserves_seeds() -> None:
    match = first_legal_playout("oware")
    assert sum(match.state.stores) == 48
    assert match.state.board == ((0,) * 6, (0,) * 6)
