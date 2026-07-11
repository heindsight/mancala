from helpers import make_state

from mancala.cli import describe_move, describe_result, render_board
from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.state import Player

NAMES = {Player.SOUTH: "Heinrich", Player.NORTH: "Nora"}


def test_render_board_puts_the_current_player_on_the_bottom() -> None:
    state = make_state(south=(4, 4, 4, 4, 4, 4), north=(4, 4, 4, 4, 4, 12), stores=(7, 0))
    assert render_board(state, NAMES) == (
        "Nora (store: 0)\n"
        "    (6)   (5)   (4)   (3)   (2)   (1)\n"
        "    [12]  [ 4]  [ 4]  [ 4]  [ 4]  [ 4]\n"
        "    [ 4]  [ 4]  [ 4]  [ 4]  [ 4]  [ 4]\n"
        "    (1)   (2)   (3)   (4)   (5)   (6)\n"
        "Heinrich (store: 7)"
    )


def test_render_board_flips_for_the_other_player() -> None:
    state = make_state(
        south=(1, 2, 3, 4, 5, 6),
        north=(0, 0, 0, 0, 0, 0),
        stores=(3, 9),
        player=Player.NORTH,
    )
    assert render_board(state, NAMES) == (
        "Heinrich (store: 3)\n"
        "    (6)   (5)   (4)   (3)   (2)   (1)\n"
        "    [ 6]  [ 5]  [ 4]  [ 3]  [ 2]  [ 1]\n"
        "    [ 0]  [ 0]  [ 0]  [ 0]  [ 0]  [ 0]\n"
        "    (1)   (2)   (3)   (4)   (5)   (6)\n"
        "Nora (store: 9)"
    )


def test_describe_move_summarises_sowing_and_details_captures() -> None:
    events = (
        SeedSown(Player.SOUTH, 3),
        SeedSown(Player.SOUTH, 4),
        SeedStored(Player.SOUTH),
        Captured(by=Player.SOUTH, owner=Player.SOUTH, cup=1, seeds=1),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=4, seeds=5),
    )
    assert describe_move(Player.SOUTH, 2, events, NAMES) == [
        "Heinrich sows 3 seeds from cup 3.",
        "Heinrich collects 1 seed from cup 2.",
        "Heinrich captures 5 seeds from Nora's cup 5.",
    ]


def test_describe_move_reports_extra_turns_and_game_over() -> None:
    events = (SeedStored(Player.NORTH), ExtraTurn(Player.NORTH))
    assert describe_move(Player.NORTH, 5, events, NAMES) == [
        "Nora sows 1 seed from cup 6.",
        "Nora gets an extra turn!",
    ]
    events = (SeedSown(Player.NORTH, 0), GameOver(None))
    assert describe_move(Player.SOUTH, 0, events, NAMES) == [
        "Heinrich sows 1 seed from cup 1.",
        "The game is over.",
    ]


def test_describe_result_announces_winner_or_draw() -> None:
    won = make_state(south=(0,) * 6, north=(0,) * 6, stores=(26, 22))
    drawn = make_state(south=(0,) * 6, north=(0,) * 6, stores=(24, 24))
    assert describe_result(won, Player.SOUTH, NAMES) == "Heinrich wins 26-22!"
    assert describe_result(drawn, None, NAMES) == "It's a draw, 24-24."
