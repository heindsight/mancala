from mancala.state import GameState, Player


def test_opponent_is_the_other_player() -> None:
    assert Player.SOUTH.opponent is Player.NORTH
    assert Player.NORTH.opponent is Player.SOUTH


def test_game_state_is_hashable_and_value_equal() -> None:
    # History tracking (Oware repetition, AI transposition tables) relies on
    # value equality and hashing of GameState.
    a = GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH
    )
    b = GameState(
        board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH
    )
    assert a == b
    assert hash(a) == hash(b)
    assert a in {b}
