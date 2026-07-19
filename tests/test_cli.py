import io
import re

import pytest
from helpers import make_state

from mancala import variants
from mancala.cli import describe_move, describe_result, main, render_board
from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.match import Match
from mancala.state import Player

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


def _run(argv: list[str], user_input: str) -> tuple[int, str]:
    stdout = io.StringIO()
    code = main(argv, stdin=io.StringIO(user_input), stdout=stdout)
    return code, stdout.getvalue()


def _assert_in_order(output: str, fragments: list[str]) -> None:
    cursor = 0
    for fragment in fragments:
        found = output.find(fragment, cursor)
        assert found != -1, f"missing (or out of order): {fragment!r}\nin:\n{output}"
        cursor = found + len(fragment)


def _assert_result_line_conserves(output: str, total: int) -> None:
    line = output.rstrip("\n").splitlines()[-1]
    assert re.fullmatch(r".+ wins \d+-\d+!|It's a draw, \d+-\d+\.", line), line
    assert sum(int(n) for n in re.findall(r"\d+", line)) == total


def test_the_main_loop_narrates_moves_and_flips_the_prompt_between_players() -> None:
    # Two hand-computed south moves (the first grants an extra turn) then EOF.
    # Expected narration is derived by hand, not from the engine.
    code, output = _run(["Ana", "Ben"], "3\n2\n")
    assert code == 1
    _assert_in_order(
        output,
        [
            "Ana, choose a cup (1-6): Ana sows 4 seeds from cup 3.\n",
            "Ana gets an extra turn!\n",
            "Ana (store: 1)\n",  # the stored seed shows on the next board
            "Ana, choose a cup (1-6): Ana sows 4 seeds from cup 2.\n",
            "Ben, choose a cup (1-6): \n",  # the turn passed to Ben
            "Game abandoned.\n",
        ],
    )
    assert output.count("choose a cup (1-6): ") == 3
    assert output.endswith("Game abandoned.\n")


@pytest.mark.parametrize("variant", ["kalah", "oware"])
def test_a_completed_game_announces_a_result_with_all_seeds_accounted_for(
    variant: str,
) -> None:
    # The engine only supplies a legal move sequence that reaches game over; the
    # assertions are engine-independent (well-formed result line, seeds conserved,
    # final board empty), so a shared rules bug cannot make both sides agree.
    match = Match(variants.get(variant))
    moves: list[int] = []
    while not match.is_over:
        move = match.rules.legal_moves(match.state)[0]
        match.play(move)
        moves.append(move)

    code, output = _run(
        [f"--variant={variant}", "Ana", "Ben"], "".join(f"{m + 1}\n" for m in moves)
    )

    assert code == 0
    _assert_result_line_conserves(output, total=48)
    assert "    [ 0]  [ 0]  [ 0]  [ 0]  [ 0]  [ 0]" in output  # terminal board


def test_bad_input_reprompts_without_crashing() -> None:
    code, output = _run([], "x\n0\n7\n")
    assert code == 1  # input exhausted -> abandoned
    assert "'x' is not a number between 1 and 6." in output
    assert "0 is not a number between 1 and 6." in output
    assert "7 is not a number between 1 and 6." in output
    assert output.count("choose a cup (1-6): ") == 4  # initial prompt + one per reject
    assert output.endswith("Game abandoned.\n")


def test_illegal_moves_are_reported_and_reprompted() -> None:
    # Kalah: cup 3 from the start lands in the store (extra turn); playing
    # the now-empty cup 3 again is illegal.
    code, output = _run(["--variant", "kalah"], "3\n3\n")
    assert code == 1
    assert "Player 1 sows 4 seeds from cup 3." in output
    assert "Player 1 gets an extra turn!" in output
    assert "Cup 3 is not a legal move." in output
    assert output.count("choose a cup (1-6): ") == 3  # move, reprompt, EOF
    assert output.endswith("Game abandoned.\n")


def test_explicit_valid_seed_count_is_used_for_the_initial_board() -> None:
    code, output = _run(["--variant", "kalah", "--seeds", "3"], "")
    assert code == 1  # immediate EOF
    assert "[ 3]" in output  # cups built with three seeds each
    assert output.endswith("Game abandoned.\n")


def test_immediate_eof_abandons_the_game_after_one_prompt() -> None:
    code, output = _run([], "")
    assert code == 1
    assert output.count("choose a cup (1-6): ") == 1
    assert output.endswith("Game abandoned.\n")


def test_oware_rejects_nonstandard_seed_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(
            ["--variant", "oware", "--seeds", "5"],
            stdin=io.StringIO(""),
            stdout=io.StringIO(),
        )
    assert exc.value.code == 2
    assert "oware is played with exactly 4 seeds per cup" in capsys.readouterr().err


def test_kalah_rejects_out_of_range_seed_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(
            ["--variant", "kalah", "--seeds", "2"],
            stdin=io.StringIO(""),
            stdout=io.StringIO(),
        )
    assert exc.value.code == 2
    assert "kalah supports 3-6 seeds per cup" in capsys.readouterr().err


def test_unknown_variant_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--variant", "senet"], stdin=io.StringIO(""), stdout=io.StringIO())
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice: 'senet'" in err


def test_more_than_two_names_are_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["Ana", "Ben", "Cara"], stdin=io.StringIO(""), stdout=io.StringIO())
    assert exc.value.code == 2
    assert "error: unrecognized arguments: Cara\n" in capsys.readouterr().err
