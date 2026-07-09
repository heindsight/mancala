import pytest
from helpers import make_state

from mancala.events import Captured, GameOver, SeedSown
from mancala.match import Match
from mancala.state import Player
from mancala.variants.oware import Oware

OWARE = Oware()


def test_initial_state_is_six_cups_of_four() -> None:
    state = OWARE.initial_state()
    assert state.board == ((4,) * 6, (4,) * 6)
    assert state.stores == (0, 0)
    assert state.current_player is Player.SOUTH


@pytest.mark.parametrize("seeds", [3, 5, 6])
def test_initial_state_rejects_anything_but_four_seeds(seeds: int) -> None:
    with pytest.raises(ValueError, match="4 seeds"):
        OWARE.initial_state(seeds_per_cup=seeds)


def test_legal_moves_are_the_movers_nonempty_cups() -> None:
    state = make_state(south=(0, 2, 0, 0, 1, 0), north=(4, 4, 4, 4, 4, 4))
    assert OWARE.legal_moves(state) == (1, 4)


def test_starved_opponent_restricts_moves_to_feeding_ones() -> None:
    # North is empty: south cup 0 (1 seed reaches cup 1 only) cannot feed;
    # cup 5 (3 seeds reach north cups 0-2) can.
    state = make_state(south=(1, 0, 0, 0, 0, 3), north=(0,) * 6)
    assert OWARE.legal_moves(state) == (5,)


def test_no_legal_moves_when_starved_opponent_cannot_be_fed() -> None:
    state = make_state(south=(1, 1, 0, 0, 0, 0), north=(0,) * 6)
    assert OWARE.legal_moves(state) == ()


def test_sowing_crosses_into_the_opponents_row() -> None:
    state = make_state(south=(0, 0, 0, 4, 0, 0), north=(4, 4, 4, 4, 4, 4))
    result = OWARE.apply_move(state, 3)
    assert result.state.board[Player.SOUTH.value] == (0, 0, 0, 0, 1, 1)
    assert result.state.board[Player.NORTH.value] == (5, 5, 4, 4, 4, 4)
    assert result.state.stores == (0, 0)
    assert result.state.current_player is Player.NORTH
    assert result.events == (
        SeedSown(Player.SOUTH, 4),
        SeedSown(Player.SOUTH, 5),
        SeedSown(Player.NORTH, 0),
        SeedSown(Player.NORTH, 1),
    )


def test_twelve_or_more_seeds_skip_the_origin_cup() -> None:
    state = make_state(south=(12, 0, 0, 0, 0, 0), north=(1, 1, 1, 1, 1, 1))
    result = OWARE.apply_move(state, 0)
    # 11 seeds fill own cups 1-5 and all north cups; the 12th skips the
    # origin and lands in own cup 1.
    assert result.state.board[Player.SOUTH.value] == (0, 2, 1, 1, 1, 1)
    assert result.state.board[Player.NORTH.value] == (2, 2, 2, 2, 2, 2)
    assert SeedSown(Player.SOUTH, 0) not in result.events


def test_capture_chains_backward_through_twos_and_threes() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 3), north=(1, 1, 1, 1, 1, 1))
    result = OWARE.apply_move(state, 5)
    # Seeds land in north cups 0-2, making each 2; all three are captured,
    # landing cup first.
    assert result.state.board[Player.NORTH.value] == (0, 0, 0, 1, 1, 1)
    assert result.state.stores == (6, 0)
    assert result.events[-3:] == (
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=2, seeds=2),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=1, seeds=2),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=0, seeds=2),
    )


def test_capture_chain_stops_at_a_cup_not_holding_two_or_three() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 4), north=(1, 1, 4, 1, 0, 0))
    result = OWARE.apply_move(state, 5)
    # Landing cup is north 3 (now 2): captured. North 2 holds 5: chain stops.
    assert result.state.board[Player.NORTH.value] == (2, 2, 5, 0, 0, 0)
    assert result.state.stores == (2, 0)
    assert [e for e in result.events if isinstance(e, Captured)] == [
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=3, seeds=2)
    ]


def test_landing_in_your_own_row_never_captures() -> None:
    state = make_state(south=(2, 0, 3, 0, 0, 0), north=(1, 2, 0, 0, 0, 0))
    result = OWARE.apply_move(state, 0)  # lands in own cup 2
    assert result.state.stores == (0, 0)
    assert not any(isinstance(e, Captured) for e in result.events)


def test_grand_slam_capture_is_forfeited() -> None:
    state = make_state(south=(1, 0, 0, 0, 0, 2), north=(1, 1, 0, 0, 0, 0))
    result = OWARE.apply_move(state, 5)
    # The chain (north cups 1 and 0, both at 2) would take all north's seeds.
    assert result.state.board[Player.NORTH.value] == (2, 2, 0, 0, 0, 0)
    assert result.state.stores == (0, 0)
    assert not any(isinstance(e, Captured) for e in result.events)


def test_capturing_more_than_half_the_seeds_ends_the_game() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 1), north=(1, 1, 1, 1, 1, 1), stores=(23, 18))
    result = OWARE.apply_move(state, 5)
    # South captures north cup 0 (now 2): store reaches 25 (> 24). Game over;
    # north's remaining 5 seeds are swept to north's store.
    assert result.state.board == ((0,) * 6, (0,) * 6)
    assert result.state.stores == (25, 23)
    assert result.events[-1] == GameOver(Player.SOUTH)
    assert OWARE.is_over(result.state)
    assert OWARE.winner(result.state) is Player.SOUTH


def test_unfeedable_starved_opponent_ends_the_game() -> None:
    # North moves its last seed into south's row; south then cannot feed the
    # now-empty north (cup 0: 4 seeds reach only cup 4; cup 1: 1 seed).
    state = make_state(
        south=(3, 1, 0, 0, 0, 0),
        north=(0, 0, 0, 0, 0, 1),
        stores=(20, 23),
        player=Player.NORTH,
    )
    result = OWARE.apply_move(state, 5)
    assert result.state.board == ((0,) * 6, (0,) * 6)
    assert result.state.stores == (25, 23)  # south keeps its remaining 5 seeds
    assert result.events[-1] == GameOver(Player.SOUTH)


def test_repeated_position_ends_the_game_with_a_split() -> None:
    # Two lone seeds chase each other around the board and return to the
    # exact starting position (same player to move) after 12 moves.
    start = make_state(south=(0, 0, 0, 0, 0, 1), north=(0, 0, 0, 0, 0, 1), stores=(23, 23))
    match = Match(OWARE, start)
    for move in [5, 5, 0, 0, 1, 1, 2, 2, 3, 3, 4]:
        match.play(move)
        assert not match.is_over
    result = match.play(4)  # recreates the starting position
    assert match.is_over
    assert match.state.stores == (24, 24)  # each side keeps its own seed
    assert match.winner is None
    assert result.events[-1] == GameOver(None)


def test_ongoing_game_is_not_over() -> None:
    assert not OWARE.is_over(OWARE.initial_state())
    assert OWARE.winner(OWARE.initial_state()) is None
