import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from helpers import make_state

from mancala.engine import variants
from mancala.engine.match import Match
from mancala.engine.state import Player
from mancala.engine.variants.descriptor import VariantDescriptor
from mancala.session import save

NAMES = {Player.SOUTH: "Heinrich", Player.NORTH: "Nora"}
KALAH = variants.get("kalah")
OWARE = variants.get("oware")


def played(variant: VariantDescriptor, moves: tuple[int, ...] = (2, 0, 1)) -> Match:
    match = Match(variant.create())
    for move in moves:
        match.play(move)
    return match


def first_legal_playout(variant: VariantDescriptor) -> Match:
    match = Match(variant.create())
    while not match.is_over:
        match.play(match.rules.legal_moves(match.state)[0])
    return match


def test_a_saved_game_round_trips_through_a_file(tmp_path: Path) -> None:
    original = played(KALAH)
    file = tmp_path / "game.json"
    save.dump(KALAH, original, NAMES, file)
    variant, restored, names = save.load(file)
    assert variant.id == "kalah"
    assert restored.rules.config == original.rules.config
    assert restored.state == original.state
    assert restored.history == original.history
    assert names == NAMES


def test_a_fresh_game_round_trips() -> None:
    original = Match(OWARE.create())
    variant, restored, names = save.from_document(
        save.to_document(OWARE, original, NAMES)
    )
    assert variant.id == "oware"
    assert restored.state == original.state
    assert restored.history == ()
    assert names == NAMES


def test_a_game_with_non_default_settings_round_trips() -> None:
    original = Match(KALAH.create({"seeds_per_cup": 6}))
    original.play(0)
    _, restored, _ = save.from_document(save.to_document(KALAH, original, NAMES))
    assert restored.rules.config == original.rules.config
    assert restored.state == original.state


def test_a_finished_game_round_trips() -> None:
    original = first_legal_playout(KALAH)
    _, restored, _ = save.from_document(save.to_document(KALAH, original, NAMES))
    assert restored.is_over
    assert restored.winner is original.winner
    assert restored.history == original.history


def test_resuming_restores_the_states_oware_repetition_detection_needs() -> None:
    original = played(OWARE, moves=(0, 1, 2, 3))
    _, restored, _ = save.from_document(save.to_document(OWARE, original, NAMES))
    assert restored.history == original.history
    assert restored._seen == original._seen


def test_the_document_records_the_metadata() -> None:
    match = played(OWARE, moves=(5, 4))
    document: dict[str, Any] = save.to_document(OWARE, match, NAMES)
    assert document["format"] == save.FORMAT
    assert document["version"] == save.VERSION
    metadata = document["metadata"]
    assert metadata["variant"] == "oware"
    assert metadata["config"] == {}
    assert metadata["players"] == {"south": "Heinrich", "north": "Nora"}
    datetime.fromisoformat(metadata["saved_at"])  # raises if unparseable
    assert document["history"] == [5, 4]


def test_the_document_records_default_settings_explicitly() -> None:
    document: dict[str, Any] = save.to_document(KALAH, Match(KALAH.create()), NAMES)
    assert document["metadata"]["config"] == {"seeds_per_cup": 4}


def test_dump_writes_pretty_printed_json_with_a_trailing_newline(
    tmp_path: Path,
) -> None:
    file = tmp_path / "game.json"
    save.dump(KALAH, played(KALAH), NAMES, file)
    text = file.read_text(encoding="utf-8")
    assert text.endswith("}\n")
    assert json.loads(text)["format"] == save.FORMAT


def test_a_match_started_mid_game_cannot_be_saved() -> None:
    start = make_state(south=(1, 0, 2, 0, 0, 3), north=(4, 0, 0, 1, 0, 0))
    match = Match(KALAH.create(), start)
    with pytest.raises(save.SaveError, match="initial position"):
        save.to_document(KALAH, match, NAMES)


def test_a_match_that_did_not_start_from_its_configured_seeds_cannot_be_saved() -> None:
    start = make_state(south=(6,) * 6, north=(6,) * 6)
    match = Match(KALAH.create({"seeds_per_cup": 4}), start)
    with pytest.raises(save.SaveError, match="initial position"):
        save.to_document(KALAH, match, NAMES)


def test_load_propagates_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(OSError, match=r"game\.json"):
        save.load(tmp_path / "game.json")


def test_load_rejects_a_file_that_is_not_json(tmp_path: Path) -> None:
    file = tmp_path / "game.json"
    file.write_text("not json", encoding="utf-8")
    with pytest.raises(save.SaveError, match="not valid JSON"):
        save.load(file)


def test_a_document_that_is_not_an_object_is_rejected() -> None:
    with pytest.raises(save.SaveError, match="save document must be an object"):
        save.from_document(["moves"])


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        (
            lambda doc: doc.update(format="senet-save"),
            "not a mancala save document",
        ),
        (
            lambda doc: doc.update(version=2),
            "unsupported save version: 2",
        ),
        (
            lambda doc: doc.update(metadata=None),
            "metadata must be an object, got None",
        ),
        (
            lambda doc: doc["metadata"].update(saved_at=1234),
            "saved_at must be a string, got 1234",
        ),
        (
            lambda doc: doc["metadata"].update(players="Heinrich and Nora"),
            "players must be an object",
        ),
        (
            lambda doc: doc["metadata"]["players"].pop("north"),
            "north must be a string, got None",
        ),
        (
            lambda doc: doc["metadata"].update(variant=7),
            "variant must be a string, got 7",
        ),
        (
            lambda doc: doc["metadata"].update(variant="senet"),
            "unknown variant 'senet'",
        ),
        (
            lambda doc: doc["metadata"].update(config=None),
            "config must be an object, got None",
        ),
        (
            lambda doc: doc["metadata"]["config"].update(seeds_per_cup=9),
            "seeds_per_cup",
        ),
        (
            lambda doc: doc["metadata"]["config"].update(cups_per_side=7),
            "cups_per_side",
        ),
        (
            lambda doc: doc.update(history="2 0 1"),
            "history must be a list of moves",
        ),
        (
            lambda doc: doc.update(history=[2, None]),
            "history move 2 must be an integer, got None",
        ),
        (
            lambda doc: doc.update(history=[6]),
            "history move 1 cannot be replayed: cup 7 is not a legal move",
        ),
        (
            lambda doc: doc.update(history=[2, 2]),
            "history move 2 cannot be replayed: cup 3 is not a legal move",
        ),
        (
            lambda doc: doc["state"].update(stores=[40, 8]),
            "recorded state does not match",
        ),
        (
            lambda doc: doc["state"]["board"][0].reverse(),
            "recorded state does not match",
        ),
        (
            lambda doc: doc.update(state="whatever"),
            "recorded state does not match",
        ),
    ],
)
def test_corrupted_documents_are_rejected(
    corrupt: Callable[[dict], object], message: str
) -> None:
    document = save.to_document(KALAH, played(KALAH), NAMES)
    corrupt(document)
    with pytest.raises(save.SaveError, match=message):
        save.from_document(document)


def test_moves_beyond_the_end_of_the_game_are_rejected() -> None:
    finished = first_legal_playout(KALAH)
    document: dict[str, Any] = save.to_document(KALAH, finished, NAMES)
    document["history"].append(0)
    with pytest.raises(save.SaveError, match="cannot be replayed: the game is over"):
        save.from_document(document)
