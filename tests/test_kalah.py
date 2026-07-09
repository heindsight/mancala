import pytest
from helpers import make_state

from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.state import Player
from mancala.variants.kalah import Kalah

KALAH = Kalah()


def test_initial_state_has_four_seeds_per_cup_by_default() -> None:
    state = KALAH.initial_state()
    assert state.board == ((4,) * 6, (4,) * 6)
    assert state.stores == (0, 0)
    assert state.current_player is Player.SOUTH


def test_initial_state_accepts_three_to_six_seeds() -> None:
    assert KALAH.initial_state(seeds_per_cup=3).board == ((3,) * 6, (3,) * 6)
    assert KALAH.initial_state(seeds_per_cup=6).board == ((6,) * 6, (6,) * 6)


@pytest.mark.parametrize("seeds", [0, 1, 2, 7, -1])
def test_initial_state_rejects_unsupported_seed_counts(seeds: int) -> None:
    with pytest.raises(ValueError, match="3-6"):
        KALAH.initial_state(seeds_per_cup=seeds)


def test_legal_moves_are_the_movers_nonempty_cups() -> None:
    state = make_state(south=(0, 3, 0, 1, 0, 2), north=(4, 4, 4, 4, 4, 4))
    assert KALAH.legal_moves(state) == (1, 3, 5)


def test_legal_moves_use_the_current_players_row() -> None:
    state = make_state(south=(1, 1, 1, 1, 1, 1), north=(0, 0, 5, 0, 0, 0), player=Player.NORTH)
    assert KALAH.legal_moves(state) == (2,)


def test_simple_sow_distributes_counterclockwise_and_passes_turn() -> None:
    result = KALAH.apply_move(KALAH.initial_state(), 0)
    assert result.state.board[Player.SOUTH.value] == (0, 5, 5, 5, 5, 4)
    assert result.state.board[Player.NORTH.value] == (4, 4, 4, 4, 4, 4)
    assert result.state.stores == (0, 0)
    assert result.state.current_player is Player.NORTH
    assert result.events == (
        SeedSown(Player.SOUTH, 1),
        SeedSown(Player.SOUTH, 2),
        SeedSown(Player.SOUTH, 3),
        SeedSown(Player.SOUTH, 4),
    )


def test_last_seed_in_store_grants_extra_turn() -> None:
    result = KALAH.apply_move(KALAH.initial_state(), 2)
    assert result.state.board[Player.SOUTH.value] == (4, 4, 0, 5, 5, 5)
    assert result.state.stores == (1, 0)
    assert result.state.current_player is Player.SOUTH
    assert result.events == (
        SeedSown(Player.SOUTH, 3),
        SeedSown(Player.SOUTH, 4),
        SeedSown(Player.SOUTH, 5),
        SeedStored(Player.SOUTH),
        ExtraTurn(Player.SOUTH),
    )


def test_sowing_skips_the_opponents_store() -> None:
    # 9 seeds from south cup 5: own store, all six north cups, then own cups 0-1.
    state = make_state(south=(1, 1, 1, 0, 0, 9), north=(0, 0, 1, 0, 0, 0))
    result = KALAH.apply_move(state, 5)
    assert result.state.board[Player.SOUTH.value] == (2, 2, 1, 0, 0, 0)
    assert result.state.board[Player.NORTH.value] == (1, 1, 2, 1, 1, 1)
    assert result.state.stores == (1, 0)  # north's store untouched
    assert result.state.current_player is Player.NORTH


def test_last_seed_in_own_empty_cup_captures_opposite() -> None:
    state = make_state(south=(1, 0, 2, 0, 0, 1), north=(0, 0, 0, 0, 3, 2))
    result = KALAH.apply_move(state, 0)
    # South's seed lands in own empty cup 1; opposite is north cup 4 (3 seeds).
    assert result.state.board[Player.SOUTH.value] == (0, 0, 2, 0, 0, 1)
    assert result.state.board[Player.NORTH.value] == (0, 0, 0, 0, 0, 2)
    assert result.state.stores == (4, 0)
    assert result.state.current_player is Player.NORTH
    assert result.events == (
        SeedSown(Player.SOUTH, 1),
        Captured(by=Player.SOUTH, owner=Player.SOUTH, cup=1, seeds=1),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=4, seeds=3),
    )


def test_no_capture_when_opposite_cup_is_empty() -> None:
    state = make_state(south=(1, 0, 2, 0, 0, 1), north=(0, 0, 0, 0, 0, 2))
    result = KALAH.apply_move(state, 0)
    assert result.state.board[Player.SOUTH.value] == (0, 1, 2, 0, 0, 1)
    assert result.state.stores == (0, 0)
    assert not any(isinstance(e, Captured) for e in result.events)


def test_emptying_your_row_ends_the_game_and_sweeps() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 1), north=(2, 0, 0, 0, 0, 3), stores=(20, 22))
    result = KALAH.apply_move(state, 5)  # last seed lands in south's store
    assert result.state.board == ((0,) * 6, (0,) * 6)
    assert result.state.stores == (21, 27)
    assert not any(isinstance(e, ExtraTurn) for e in result.events)  # game end trumps extra turn
    assert result.events[-3:] == (
        Captured(by=Player.NORTH, owner=Player.NORTH, cup=0, seeds=2),
        Captured(by=Player.NORTH, owner=Player.NORTH, cup=5, seeds=3),
        GameOver(Player.NORTH),
    )
    assert KALAH.is_over(result.state)
    assert KALAH.winner(result.state) is Player.NORTH


def test_equal_stores_after_sweep_is_a_draw() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 1), north=(0, 0, 0, 0, 0, 1), stores=(23, 23))
    result = KALAH.apply_move(state, 5)
    assert result.state.stores == (24, 24)
    assert result.events[-1] == GameOver(None)
    assert KALAH.winner(result.state) is None


def test_ongoing_game_is_not_over_and_has_no_winner() -> None:
    state = KALAH.initial_state()
    assert not KALAH.is_over(state)
    assert KALAH.winner(state) is None
