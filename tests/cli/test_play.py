import io
from pathlib import Path
from typing import TextIO
from unittest.mock import MagicMock, call

import pytest
from helpers import make_state
from pytest_mock import MockerFixture

from mancala.cli.play import (
    ComputerPlayer,
    HumanPlayer,
    SaveGame,
    play_match,
    read_move,
)
from mancala.engine.match import Match
from mancala.engine.rules import Move
from mancala.engine.state import Player
from mancala.engine.variants.kalah import Kalah
from mancala.session import save

KALAH = Kalah()
NAMES = {Player.SOUTH: "Heinrich", Player.NORTH: "Nora"}
ENDGAME = make_state(south=(0, 0, 0, 0, 0, 1), north=(0,) * 6, stores=(23, 24))
PROMPT = "Ana, choose a cup (1-6) or 'save FILE': "


class ScriptedStrategy:
    """A strategy that plays a fixed sequence of moves and records the matches."""

    def __init__(self, *moves: Move) -> None:
        self._moves = iter(moves)
        self.matches: list[Match] = []

    def choose(self, match: Match) -> Move:
        self.matches.append(match)
        return next(self._moves)


def humans(stdin: TextIO, stdout: TextIO) -> tuple[HumanPlayer, HumanPlayer]:
    return HumanPlayer("Heinrich", stdin, stdout), HumanPlayer("Nora", stdin, stdout)


@pytest.fixture
def mock_read_move(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("mancala.cli.play.read_move")


@pytest.fixture
def mock_render_board(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("mancala.cli.play.render_board", return_value="<board>")


def test_read_move_returns_the_chosen_cup_as_a_zero_based_move() -> None:
    assert read_move("Ana", 6, io.StringIO("3\n"), io.StringIO()) == 2


def test_read_move_prompts_the_player_by_name() -> None:
    stdout = io.StringIO()
    read_move("Ana", 6, io.StringIO("3\n"), stdout)
    assert stdout.getvalue() == PROMPT


def test_read_move_returns_none_when_input_is_exhausted() -> None:
    assert read_move("Ana", 6, io.StringIO(""), io.StringIO()) is None


def test_read_move_returns_none_when_interrupted(mocker: MockerFixture) -> None:
    stdin = mocker.MagicMock(spec=io.StringIO)
    stdin.readline.side_effect = KeyboardInterrupt
    assert read_move("Ana", 6, stdin, io.StringIO()) is None


def test_read_move_keeps_prompting_until_the_input_is_valid() -> None:
    assert read_move("Ana", 6, io.StringIO("x\n0\n7\n3\n"), io.StringIO()) == 2


def test_read_move_explains_a_non_numeric_rejection() -> None:
    stdout = io.StringIO()
    read_move("Ana", 6, io.StringIO("x\n3\n"), stdout)
    assert stdout.getvalue() == (
        f"{PROMPT}'x' is not a number between 1 and 6.\n{PROMPT}"
    )


@pytest.mark.parametrize("cup", [0, 7])
def test_read_move_explains_an_out_of_range_rejection(cup: int) -> None:
    stdout = io.StringIO()
    read_move("Ana", 6, io.StringIO(f"{cup}\n3\n"), stdout)
    assert stdout.getvalue() == (
        f"{PROMPT}{cup} is not a number between 1 and 6.\n{PROMPT}"
    )


def test_read_move_offers_every_cup_on_the_board() -> None:
    stdout = io.StringIO()
    read_move("Ana", 4, io.StringIO("3\n"), stdout)
    assert stdout.getvalue() == "Ana, choose a cup (1-4) or 'save FILE': "


def test_read_move_rejects_a_cup_beyond_the_board() -> None:
    stdout = io.StringIO()
    assert read_move("Ana", 4, io.StringIO("5\n3\n"), stdout) == 2
    assert "5 is not a number between 1 and 4.\n" in stdout.getvalue()


def test_read_move_explains_a_non_numeric_rejection_against_the_board() -> None:
    stdout = io.StringIO()
    read_move("Ana", 4, io.StringIO("x\n3\n"), stdout)
    assert "'x' is not a number between 1 and 4.\n" in stdout.getvalue()


def test_read_move_returns_a_save_request() -> None:
    stdin = io.StringIO("save saved-game.json\n")
    assert read_move("Ana", 6, stdin, io.StringIO()) == SaveGame("saved-game.json")


def test_read_move_asks_again_when_save_names_no_file() -> None:
    stdout = io.StringIO()
    assert read_move("Ana", 6, io.StringIO("save\n3\n"), stdout) == 2
    assert "Say where to save the game: 'save FILE'.\n" in stdout.getvalue()


def test_human_player_prompts_by_name_and_returns_the_move(
    mock_read_move: MagicMock,
) -> None:
    mock_read_move.return_value = 5
    stdin, stdout = io.StringIO(), io.StringIO()
    assert HumanPlayer("Ana", stdin, stdout).get_move(Match(KALAH, ENDGAME)) == 5
    assert mock_read_move.call_args_list == [call("Ana", 6, stdin, stdout)]


def test_human_player_offers_the_cups_of_the_position(
    mock_read_move: MagicMock,
) -> None:
    stdin, stdout = io.StringIO(), io.StringIO()
    match = Match(KALAH, make_state(south=(0, 0, 0, 1), north=(1, 0, 0, 0)))
    HumanPlayer("Ana", stdin, stdout).get_move(match)
    assert mock_read_move.call_args_list == [call("Ana", 4, stdin, stdout)]


def test_human_player_spec_is_its_name() -> None:
    assert HumanPlayer("Ana", io.StringIO(), io.StringIO()).spec == "Ana"


def test_computer_player_chooses_with_its_strategy() -> None:
    assert (
        ComputerPlayer("HAL", ScriptedStrategy(5), io.StringIO()).get_move(
            Match(KALAH, ENDGAME)
        )
        == 5
    )


def test_computer_player_hands_the_match_to_its_strategy() -> None:
    strategy = ScriptedStrategy(5)
    match = Match(KALAH, ENDGAME)
    ComputerPlayer("HAL", strategy, io.StringIO()).get_move(match)
    assert strategy.matches == [match]


def test_computer_player_announces_its_choice() -> None:
    stdout = io.StringIO()
    ComputerPlayer("HAL", ScriptedStrategy(5), stdout).get_move(Match(KALAH, ENDGAME))
    assert stdout.getvalue() == "HAL chooses cup 6.\n"


def test_play_match_returns_0_for_a_game_played_to_completion(
    mock_read_move: MagicMock,
) -> None:
    mock_read_move.side_effect = [5]
    stdout = io.StringIO()
    assert play_match(Match(KALAH, ENDGAME), humans(io.StringIO(), stdout), stdout) == 0


def test_play_match_returns_1_when_input_runs_out(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [None]
    stdout = io.StringIO()
    assert play_match(Match(KALAH, ENDGAME), humans(io.StringIO(), stdout), stdout) == 1


def test_play_match_reports_an_abandoned_game(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [None]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), humans(io.StringIO(), stdout), stdout)
    assert stdout.getvalue().endswith("\nGame abandoned.\n")


def test_play_match_prompts_the_current_player(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [5]
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, ENDGAME), humans(stdin, stdout), stdout)
    assert mock_read_move.call_args_list == [call("Heinrich", 6, stdin, stdout)]


def test_play_match_prompts_the_players_in_turn_order(
    mock_read_move: MagicMock,
) -> None:
    mock_read_move.side_effect = [0, 0, None]
    start = make_state(south=(1, 1, 0, 0, 0, 0), north=(1, 0, 0, 0, 0, 0))
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, start), humans(stdin, stdout), stdout)
    assert mock_read_move.call_args_list == [
        call("Heinrich", 6, stdin, stdout),
        call("Nora", 6, stdin, stdout),
        call("Heinrich", 6, stdin, stdout),
    ]


def test_play_match_prompts_the_same_player_after_an_extra_turn(
    mock_read_move: MagicMock,
) -> None:
    mock_read_move.side_effect = [5, None]
    start = make_state(south=(1, 0, 0, 0, 0, 1), north=(1, 0, 0, 0, 0, 0))
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, start), humans(stdin, stdout), stdout)
    assert mock_read_move.call_args_list == [call("Heinrich", 6, stdin, stdout)] * 2


def test_play_match_narrates_the_move(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [5]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), humans(io.StringIO(), stdout), stdout)
    assert "Heinrich sows 1 seed from cup 6.\nThe game is over.\n" in stdout.getvalue()


def test_play_match_announces_the_result(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [5]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), humans(io.StringIO(), stdout), stdout)
    assert stdout.getvalue().endswith("It's a draw, 24-24.\n")


def test_play_match_renders_the_board_before_the_move_and_after_the_game(
    mock_render_board: MagicMock, mock_read_move: MagicMock
) -> None:
    mock_read_move.side_effect = [5]
    match = Match(KALAH, ENDGAME)
    stdout = io.StringIO()
    play_match(match, humans(io.StringIO(), stdout), stdout)
    assert mock_render_board.call_args_list == [
        call(ENDGAME, NAMES),
        call(match.state, NAMES),
    ]


def test_play_match_renders_the_current_position_each_round(
    mock_render_board: MagicMock, mock_read_move: MagicMock
) -> None:
    mock_read_move.side_effect = [0, 0, None]
    start = make_state(south=(1, 1, 0, 0, 0, 0), north=(1, 0, 0, 0, 0, 0))
    stdout = io.StringIO()
    play_match(Match(KALAH, start), humans(io.StringIO(), stdout), stdout)
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


def test_play_match_saves_the_game_and_exits(
    mock_read_move: MagicMock, tmp_path: Path
) -> None:
    file = tmp_path / "game.json"
    mock_read_move.side_effect = [0, SaveGame(str(file))]
    match = Match(KALAH)
    stdout = io.StringIO()
    assert play_match(match, humans(io.StringIO(), stdout), stdout) == 0
    assert stdout.getvalue().endswith(f"Game saved to {file}.\n")
    restored, specs = save.load(file)
    assert restored.state == match.state
    assert restored.history == match.history
    assert specs == NAMES


def test_play_match_records_a_computer_players_spec(tmp_path: Path) -> None:
    file = tmp_path / "game.json"
    stdout = io.StringIO()
    human = HumanPlayer("Nora", io.StringIO(f"save {file}\n"), stdout)
    computer = ComputerPlayer("Computer (hard)", ScriptedStrategy(), stdout, "cpu:hard")
    assert play_match(Match(KALAH), (human, computer), stdout) == 0
    _, specs = save.load(file)
    assert specs == {Player.SOUTH: "Nora", Player.NORTH: "cpu:hard"}


def test_play_match_keeps_playing_when_saving_fails(
    mock_read_move: MagicMock, tmp_path: Path
) -> None:
    file = tmp_path / "missing-directory" / "game.json"
    mock_read_move.side_effect = [SaveGame(str(file)), None]
    stdout = io.StringIO()
    assert play_match(Match(KALAH), humans(io.StringIO(), stdout), stdout) == 1
    assert "Could not save: " in stdout.getvalue()


def test_play_match_reports_an_illegal_move(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [0, 5]
    stdout = io.StringIO()
    play_match(Match(KALAH, ENDGAME), humans(io.StringIO(), stdout), stdout)
    assert "Cup 1 is not a legal move.\n" in stdout.getvalue()


def test_play_match_asks_again_after_an_illegal_move(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [0, 5]
    stdin, stdout = io.StringIO(), io.StringIO()
    play_match(Match(KALAH, ENDGAME), humans(stdin, stdout), stdout)
    assert mock_read_move.call_args_list == [call("Heinrich", 6, stdin, stdout)] * 2


def test_play_match_lets_a_computer_move_without_prompting(
    mock_read_move: MagicMock,
) -> None:
    stdout = io.StringIO()
    computer = ComputerPlayer("Heinrich", ScriptedStrategy(5), stdout)
    _, north = humans(io.StringIO(), stdout)
    assert play_match(Match(KALAH, ENDGAME), (computer, north), stdout) == 0
    mock_read_move.assert_not_called()


def test_play_match_still_prompts_the_human_side(mock_read_move: MagicMock) -> None:
    mock_read_move.side_effect = [0, None]
    start = make_state(south=(1, 1, 0, 0, 0, 0), north=(1, 0, 0, 0, 0, 0))
    stdin, stdout = io.StringIO(), io.StringIO()
    south, _ = humans(stdin, stdout)
    computer = ComputerPlayer("Nora", ScriptedStrategy(0), stdout)
    play_match(Match(KALAH, start), (south, computer), stdout)
    assert mock_read_move.call_args_list == [call("Heinrich", 6, stdin, stdout)] * 2
