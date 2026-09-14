import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from mancala.cli.main import main
from mancala.cli.play import ComputerPlayer, HumanPlayer
from mancala.engine import variants
from mancala.engine.match import Match
from mancala.engine.state import Player
from mancala.engine.variants.kalah import Kalah, KalahConfig
from mancala.engine.variants.oware import Oware
from mancala.session import save

KALAH = Kalah(KalahConfig())
NAMES = {Player.SOUTH: "Heinrich", Player.NORTH: "Nora"}


@pytest.fixture
def mock_play_match(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("mancala.cli.main.play_match", return_value=0)


def test_main_plays_the_requested_variant(mock_play_match: MagicMock) -> None:
    main(["new", "--variant", "oware"])
    variant, match, _, _ = mock_play_match.call_args.args
    assert variant.id == "oware"
    assert isinstance(match.rules, Oware)


def test_main_builds_the_initial_board_with_the_requested_seeds(
    mock_play_match: MagicMock,
) -> None:
    main(["new", "--seeds", "3"])
    expected = Kalah(KalahConfig(seeds_per_cup=3)).initial_state()
    assert mock_play_match.call_args.args[1].state == expected


def test_main_assigns_the_player_names(mock_play_match: MagicMock) -> None:
    main(["new", "Ana", "Ben"])
    assert [player.name for player in mock_play_match.call_args.args[2]] == [
        "Ana",
        "Ben",
    ]


def test_main_defaults_the_player_names(mock_play_match: MagicMock) -> None:
    main(["new"])
    assert [player.name for player in mock_play_match.call_args.args[2]] == [
        "Player 1",
        "Player 2",
    ]


def test_main_seats_two_humans_for_hot_seat_play(mock_play_match: MagicMock) -> None:
    main(["new"])
    south, north = mock_play_match.call_args.args[2]
    assert isinstance(south, HumanPlayer)
    assert isinstance(north, HumanPlayer)


def test_main_puts_a_computer_on_north(mock_play_match: MagicMock) -> None:
    main(["new", "Ana", "cpu:easy"])
    south, north = mock_play_match.call_args.args[2]
    assert isinstance(south, HumanPlayer)
    assert isinstance(north, ComputerPlayer)


def test_main_puts_a_computer_on_south(mock_play_match: MagicMock) -> None:
    main(["new", "cpu:easy", "Ben"])
    south, north = mock_play_match.call_args.args[2]
    assert isinstance(south, ComputerPlayer)
    assert isinstance(north, HumanPlayer)


def test_main_seats_two_computers(mock_play_match: MagicMock) -> None:
    main(["new", "cpu:easy", "cpu:hard"])
    south, north = mock_play_match.call_args.args[2]
    assert isinstance(south, ComputerPlayer)
    assert isinstance(north, ComputerPlayer)


@pytest.mark.usefixtures("mock_play_match")
def test_main_builds_the_strategy_for_the_chosen_difficulty(
    mocker: MockerFixture,
) -> None:
    get = mocker.patch("mancala.cli.main.strategies.get")
    main(["new", "Ana", "cpu:hard"])
    get.assert_called_once_with("hard")


def test_main_names_the_computer_after_its_difficulty(
    mock_play_match: MagicMock,
) -> None:
    main(["new", "Ana", "cpu:medium"])
    _, north = mock_play_match.call_args.args[2]
    assert north.name == "Computer (medium)"


def test_main_treats_a_bare_cpu_as_a_human_name(mock_play_match: MagicMock) -> None:
    main(["new", "cpu", "Ben"])
    south, _ = mock_play_match.call_args.args[2]
    assert isinstance(south, HumanPlayer)
    assert south.name == "cpu"


def test_main_rejects_an_unknown_difficulty(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["new", "Ana", "cpu:grandmaster"])
    assert exc.value.code == 2
    assert "unknown difficulty 'grandmaster'" in capsys.readouterr().err


def test_main_rejects_an_empty_difficulty(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["new", "Ana", "cpu:"])
    assert exc.value.code == 2
    assert "unknown difficulty ''" in capsys.readouterr().err


def test_main_passes_the_output_stream_to_the_match_loop(
    mock_play_match: MagicMock,
) -> None:
    stdout = io.StringIO()
    main(["new"], stdin=io.StringIO(), stdout=stdout)
    assert mock_play_match.call_args.args[3] is stdout


def test_main_gives_the_human_players_the_supplied_input_stream(
    mock_play_match: MagicMock,
) -> None:
    main(["new"], stdin=io.StringIO("3\n"), stdout=io.StringIO())
    _, match, (south, _), _ = mock_play_match.call_args.args
    assert south.get_move(match) == 2


def test_main_defaults_to_the_process_output_stream(
    mock_play_match: MagicMock,
) -> None:
    main(["new"])
    assert mock_play_match.call_args.args[3] is sys.stdout


def test_main_defaults_to_the_process_input_stream(
    mock_play_match: MagicMock, mocker: MockerFixture
) -> None:
    mocker.patch.object(sys, "stdin", io.StringIO("3\n"))
    main(["new"])
    _, match, (south, _), _ = mock_play_match.call_args.args
    assert south.get_move(match) == 2


def test_main_returns_the_match_loops_exit_code(mock_play_match: MagicMock) -> None:
    mock_play_match.return_value = 1
    assert main(["new"]) == 1


def test_main_requires_a_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    assert "arguments are required: command" in capsys.readouterr().err


def test_main_resumes_a_saved_game(mock_play_match: MagicMock, tmp_path: Path) -> None:
    oware = variants.get("oware")
    original = Match(oware.create())
    original.play(2)
    original.play(4)
    file = tmp_path / "game.json"
    save.dump(oware, original, NAMES, file)
    main(["resume", str(file)])
    variant, restored, _, _ = mock_play_match.call_args.args
    assert variant.id == "oware"
    assert isinstance(restored.rules, Oware)
    assert restored.state == original.state
    assert restored.history == original.history


def test_main_resumes_the_saved_player_names(
    mock_play_match: MagicMock, tmp_path: Path
) -> None:
    file = tmp_path / "game.json"
    save.dump(variants.get("kalah"), Match(KALAH), NAMES, file)
    main(["resume", str(file)])
    assert [player.name for player in mock_play_match.call_args.args[2]] == [
        "Heinrich",
        "Nora",
    ]


def test_main_resumes_a_computer_player(
    mock_play_match: MagicMock, tmp_path: Path
) -> None:
    file = tmp_path / "game.json"
    specs = {Player.SOUTH: "cpu:hard", Player.NORTH: "Nora"}
    save.dump(variants.get("kalah"), Match(KALAH), specs, file)
    main(["resume", str(file)])
    south, north = mock_play_match.call_args.args[2]
    assert isinstance(south, ComputerPlayer)
    assert south.name == "Computer (hard)"
    assert isinstance(north, HumanPlayer)


def test_main_rejects_a_missing_save_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["resume", str(tmp_path / "game.json")])
    assert exc.value.code == 2
    assert "game.json" in capsys.readouterr().err


def test_main_rejects_an_invalid_save_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    file = tmp_path / "game.json"
    file.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["resume", str(file)])
    assert exc.value.code == 2
    assert "not a mancala save document" in capsys.readouterr().err


def test_resume_requires_a_file(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["resume"])
    assert exc.value.code == 2
    assert "arguments are required: file" in capsys.readouterr().err


def test_oware_refuses_a_seed_count_rather_than_ignoring_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["new", "--variant", "oware", "--seeds", "4"])
    assert exc.value.code == 2
    assert "seeds_per_cup" in capsys.readouterr().err


def test_kalah_rejects_out_of_range_seed_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["new", "--variant", "kalah", "--seeds", "2"])
    assert exc.value.code == 2
    assert "seeds_per_cup" in capsys.readouterr().err


def test_unknown_variant_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["new", "--variant", "senet"])
    assert exc.value.code == 2
    assert "invalid choice: 'senet'" in capsys.readouterr().err


def test_more_than_two_names_are_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["new", "Ana", "Ben", "Cara"])
    assert exc.value.code == 2
    assert "error: unrecognized arguments: Cara\n" in capsys.readouterr().err
