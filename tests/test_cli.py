import io
import sys
from unittest.mock import MagicMock, call

import pytest
from helpers import make_state
from pytest_mock import MockerFixture

from mancala import variants
from mancala.cli import (
    describe_move,
    describe_result,
    main,
    play_match,
    read_move,
    render_board,
)
from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.match import Match
from mancala.state import Player
from mancala.variants.kalah import Kalah

KALAH = Kalah()
NAMES = {Player.SOUTH: "Heinrich", Player.NORTH: "Nora"}
ENDGAME = make_state(south=(0, 0, 0, 0, 0, 1), north=(0,) * 6, stores=(23, 24))


@pytest.fixture
def mock_read_move(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("mancala.cli.read_move")


@pytest.fixture
def mock_render_board(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("mancala.cli.render_board", return_value="<board>")


@pytest.fixture
def mock_play_match(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("mancala.cli.play_match", return_value=0)


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


def test_read_move_returns_the_chosen_cup_as_a_zero_based_move() -> None:
    assert read_move("Ana", io.StringIO("3\n"), io.StringIO()) == 2


def test_read_move_prompts_the_player_by_name() -> None:
    stdout = io.StringIO()
    read_move("Ana", io.StringIO("3\n"), stdout)
    assert stdout.getvalue() == "Ana, choose a cup (1-6): "


def test_read_move_returns_none_when_input_is_exhausted() -> None:
    assert read_move("Ana", io.StringIO(""), io.StringIO()) is None


def test_read_move_returns_none_when_interrupted(mocker: MockerFixture) -> None:
    stdin = mocker.MagicMock(spec=io.StringIO)
    stdin.readline.side_effect = KeyboardInterrupt
    assert read_move("Ana", stdin, io.StringIO()) is None


def test_read_move_keeps_prompting_until_the_input_is_valid() -> None:
    assert read_move("Ana", io.StringIO("x\n0\n7\n3\n"), io.StringIO()) == 2


def test_read_move_explains_a_non_numeric_rejection() -> None:
    stdout = io.StringIO()
    read_move("Ana", io.StringIO("x\n3\n"), stdout)
    assert stdout.getvalue() == (
        "Ana, choose a cup (1-6): 'x' is not a number between 1 and 6.\n"
        "Ana, choose a cup (1-6): "
    )


@pytest.mark.parametrize("cup", [0, 7])
def test_read_move_explains_an_out_of_range_rejection(cup: int) -> None:
    stdout = io.StringIO()
    read_move("Ana", io.StringIO(f"{cup}\n3\n"), stdout)
    assert stdout.getvalue() == (
        f"Ana, choose a cup (1-6): {cup} is not a number between 1 and 6.\n"
        "Ana, choose a cup (1-6): "
    )


def test_play_match_returns_0_for_a_game_played_to_completion(
    mock_read_move: MagicMock,
) -> None:
    mock_read_move.side_effect = [5]
    assert play_match(Match(KALAH, ENDGAME), NAMES, io.StringIO(), io.StringIO()) == 0


def test_play_match_returns_1_when_input_runs_out(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [None]
    assert play_match(Match(KALAH, ENDGAME), NAMES, io.StringIO(), io.StringIO()) == 1


def test_play_match_reports_an_abandoned_game(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [None]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), NAMES, io.StringIO(), stdout)
    assert stdout.getvalue().endswith("\nGame abandoned.\n")


def test_play_match_prompts_the_current_player(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [5]
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, ENDGAME), NAMES, stdin, stdout)
    assert mock_read_move.call_args_list == [call("Heinrich", stdin, stdout)]


def test_play_match_prompts_the_players_in_turn_order(
    mock_read_move: MagicMock,
) -> None:
    mock_read_move.side_effect = [0, 0, None]
    start = make_state(south=(1, 1, 0, 0, 0, 0), north=(1, 0, 0, 0, 0, 0))
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, start), NAMES, stdin, stdout)
    assert mock_read_move.call_args_list == [
        call("Heinrich", stdin, stdout),
        call("Nora", stdin, stdout),
        call("Heinrich", stdin, stdout),
    ]


def test_play_match_prompts_the_same_player_after_an_extra_turn(
    mock_read_move: MagicMock,
) -> None:
    mock_read_move.side_effect = [5, None]
    start = make_state(south=(1, 0, 0, 0, 0, 1), north=(1, 0, 0, 0, 0, 0))
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, start), NAMES, stdin, stdout)
    assert mock_read_move.call_args_list == [call("Heinrich", stdin, stdout)] * 2


def test_play_match_narrates_the_move(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [5]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), NAMES, io.StringIO(), stdout)
    assert "Heinrich sows 1 seed from cup 6.\nThe game is over.\n" in stdout.getvalue()


def test_play_match_announces_the_result(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [5]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), NAMES, io.StringIO(), stdout)
    assert stdout.getvalue().endswith("It's a draw, 24-24.\n")


def test_play_match_renders_the_board_before_the_move_and_after_the_game(
    mock_render_board: MagicMock, mock_read_move: MagicMock
) -> None:
    mock_read_move.side_effect = [5]
    match = Match(KALAH, ENDGAME)
    play_match(match, NAMES, io.StringIO(), io.StringIO())
    assert mock_render_board.call_args_list == [
        call(ENDGAME, NAMES),
        call(match.state, NAMES),
    ]


def test_play_match_renders_the_current_position_each_round(
    mock_render_board: MagicMock, mock_read_move: MagicMock
) -> None:
    mock_read_move.side_effect = [0, 0, None]
    start = make_state(south=(1, 1, 0, 0, 0, 0), north=(1, 0, 0, 0, 0, 0))
    play_match(Match(KALAH, start), NAMES, io.StringIO(), io.StringIO())
    assert mock_render_board.call_args_list == [
        call(start, NAMES),
        call(
            make_state(
                south=(0, 2, 0, 0, 0, 0),
                north=(1, 0, 0, 0, 0, 0),
                player=Player.NORTH,
            ),
            NAMES,
        ),
        call(make_state(south=(0, 2, 0, 0, 0, 0), north=(0, 1, 0, 0, 0, 0)), NAMES),
    ]


def test_play_match_reports_an_illegal_move(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [0, 5]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), NAMES, io.StringIO(), stdout)
    assert "Cup 1 is not a legal move.\n" in stdout.getvalue()


def test_play_match_asks_again_after_an_illegal_move(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [0, 5]
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, ENDGAME), NAMES, stdin, stdout)
    assert mock_read_move.call_args_list == [call("Heinrich", stdin, stdout)] * 2


def test_main_plays_the_requested_variant(mock_play_match: MagicMock) -> None:
    main(["--variant", "oware"])
    assert mock_play_match.call_args.args[0].rules is variants.get("oware")


def test_main_builds_the_initial_board_with_the_requested_seeds(
    mock_play_match: MagicMock,
) -> None:
    main(["--seeds", "3"])
    assert mock_play_match.call_args.args[0].state == KALAH.initial_state(3)


def test_main_assigns_the_player_names(mock_play_match: MagicMock) -> None:
    main(["Ana", "Ben"])
    assert mock_play_match.call_args.args[1] == {
        Player.SOUTH: "Ana",
        Player.NORTH: "Ben",
    }


def test_main_defaults_the_player_names(mock_play_match: MagicMock) -> None:
    main([])
    assert mock_play_match.call_args.args[1] == {
        Player.SOUTH: "Player 1",
        Player.NORTH: "Player 2",
    }


def test_main_passes_the_streams_to_the_match_loop(mock_play_match: MagicMock) -> None:
    stdin, stdout = io.StringIO(), io.StringIO()
    main([], stdin=stdin, stdout=stdout)
    assert mock_play_match.call_args.args[2:] == (stdin, stdout)


def test_main_defaults_to_the_process_streams(mock_play_match: MagicMock) -> None:
    main([])
    assert mock_play_match.call_args.args[2:] == (sys.stdin, sys.stdout)


def test_main_returns_the_match_loops_exit_code(mock_play_match: MagicMock) -> None:
    mock_play_match.return_value = 1
    assert main([]) == 1


def test_oware_rejects_nonstandard_seed_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--variant", "oware", "--seeds", "5"])
    assert exc.value.code == 2
    assert "oware is played with exactly 4 seeds per cup" in capsys.readouterr().err


def test_kalah_rejects_out_of_range_seed_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--variant", "kalah", "--seeds", "2"])
    assert exc.value.code == 2
    assert "kalah supports 3-6 seeds per cup" in capsys.readouterr().err


def test_unknown_variant_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--variant", "senet"])
    assert exc.value.code == 2
    assert "invalid choice: 'senet'" in capsys.readouterr().err


def test_more_than_two_names_are_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["Ana", "Ben", "Cara"])
    assert exc.value.code == 2
    assert "error: unrecognized arguments: Cara\n" in capsys.readouterr().err
