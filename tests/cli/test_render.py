import pytest
from helpers import make_state

from mancala.cli.render import describe_move, describe_result, render_board
from mancala.engine.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.engine.state import Player

NAMES = {Player.SOUTH: "Heinrich", Player.NORTH: "Nora"}


def test_render_board_puts_the_current_player_on_the_bottom() -> None:
    state = make_state(
        south=(4, 4, 4, 4, 4, 4), north=(4, 4, 4, 4, 4, 12), stores=(7, 0)
    )
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


def test_describe_move_summarises_the_sowing() -> None:
    events = (
        SeedSown(Player.SOUTH, 3),
        SeedSown(Player.SOUTH, 4),
        SeedStored(Player.SOUTH),
    )
    assert describe_move(Player.SOUTH, 2, events, NAMES) == [
        "Heinrich sows 3 seeds from cup 3."
    ]


def test_describe_move_uses_the_singular_for_a_single_seed() -> None:
    events = (SeedStored(Player.NORTH),)
    assert describe_move(Player.NORTH, 5, events, NAMES) == [
        "Nora sows 1 seed from cup 6."
    ]


def test_describe_move_details_captures_from_the_opponent() -> None:
    events = (
        SeedSown(Player.SOUTH, 4),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=4, seeds=5),
    )
    assert describe_move(Player.SOUTH, 3, events, NAMES) == [
        "Heinrich sows 1 seed from cup 4.",
        "Heinrich captures 5 seeds from Nora's cup 5.",
    ]


def test_describe_move_details_collections_from_the_movers_own_row() -> None:
    events = (
        SeedSown(Player.SOUTH, 1),
        Captured(by=Player.SOUTH, owner=Player.SOUTH, cup=1, seeds=2),
    )
    assert describe_move(Player.SOUTH, 0, events, NAMES) == [
        "Heinrich sows 1 seed from cup 1.",
        "Heinrich collects 2 seeds from cup 2.",
    ]


def test_describe_move_announces_an_extra_turn() -> None:
    events = (SeedStored(Player.NORTH), ExtraTurn(Player.NORTH))
    assert describe_move(Player.NORTH, 5, events, NAMES) == [
        "Nora sows 1 seed from cup 6.",
        "Nora gets an extra turn!",
    ]


def test_describe_move_announces_the_end_of_the_game() -> None:
    events = (SeedSown(Player.SOUTH, 1), GameOver(None))
    assert describe_move(Player.SOUTH, 0, events, NAMES) == [
        "Heinrich sows 1 seed from cup 1.",
        "The game is over.",
    ]


@pytest.mark.parametrize(
    ("stores", "winner", "expected"),
    [
        ((26, 22), Player.SOUTH, "Heinrich wins 26-22!"),
        ((22, 26), Player.NORTH, "Nora wins 26-22!"),
    ],
)
def test_describe_result_announces_the_winner_with_the_score(
    stores: tuple[int, int], winner: Player, expected: str
) -> None:
    state = make_state(south=(0,) * 6, north=(0,) * 6, stores=stores)
    assert describe_result(state, winner, NAMES) == expected


def test_describe_result_announces_a_draw() -> None:
    state = make_state(south=(0,) * 6, north=(0,) * 6, stores=(24, 24))
    assert describe_result(state, None, NAMES) == "It's a draw, 24-24."
