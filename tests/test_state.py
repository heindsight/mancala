from mancala.state import GameState, Player


def test_opponent_is_the_other_player() -> None:
    assert Player.SOUTH.opponent is Player.NORTH
    assert Player.NORTH.opponent is Player.SOUTH


def test_game_state_is_hashable_and_value_equal() -> None:
    a = GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH
    )
    b = GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH
    )
    assert a == b
    assert hash(a) == hash(b)
    assert a in {b}


def test_game_states_differing_in_any_field_are_not_equal() -> None:
    base = GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH
    )
    assert base != GameState(
        board=((3, 5, 4, 4, 4, 4), (4,) * 6), stores=(0, 0), current_player=Player.SOUTH
    )
    assert base != GameState(
        board=((4,) * 6, (4,) * 6), stores=(1, 0), current_player=Player.SOUTH
    )
    assert base != GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.NORTH
    )


def test_distinct_game_states_are_kept_apart_in_a_set() -> None:
    a = GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH
    )
    b = GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.NORTH
    )
    assert a not in {b}
    assert len({a, b}) == 2


def test_board_is_indexed_by_player_value() -> None:
    state = GameState(
        board=((1, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 2)),
        stores=(3, 4),
        current_player=Player.NORTH,
    )
    assert state.board[Player.SOUTH.value] == (1, 0, 0, 0, 0, 0)
    assert state.board[Player.NORTH.value] == (0, 0, 0, 0, 0, 2)
    assert state.stores[Player.NORTH.value] == 4
