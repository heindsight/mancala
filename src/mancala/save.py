"""Save and resume games as JSON documents.

A save document records metadata (variant, seed count, player specs, save
time), the move history, and the current state. A player spec is a name for a
human seat or `cpu:<difficulty>` for a computer one, so a resumed game seats
the same players. Loading replays the history
from the variant's initial position, which rebuilds everything a `Match`
tracks — including the set of seen states that Oware's repetition rule
needs — and validates the document in full: every recorded move must be
legal in sequence, and the recorded state must match the replayed one.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from mancala import variants
from mancala.match import Match
from mancala.rules import IllegalMoveError
from mancala.state import GameState, Player

FORMAT = "mancala-save"
VERSION = 1


class SaveError(Exception):
    """The save document is malformed, inconsistent, or unwritable."""


def dump(match: Match, specs: dict[Player, str], file: str | Path) -> None:
    """Write `match` to `file`. Raises SaveError or OSError on failure."""
    document = to_document(match, specs)
    Path(file).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def load(file: str | Path) -> tuple[Match, dict[Player, str]]:
    """Read a match from `file`. Raises SaveError or OSError on failure."""
    text = Path(file).read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except ValueError as error:
        raise SaveError(f"{file} is not valid JSON: {error}") from error
    return from_document(document)


def to_document(match: Match, specs: dict[Player, str]) -> dict[str, object]:
    """Serialize `match` to a JSON-compatible document."""
    initial = match.history[0][0] if match.history else match.state
    seeds = initial.board[0][0]
    try:
        expected = match.rules.initial_state(seeds)
    except ValueError:
        expected = None
    if initial != expected:
        raise SaveError("only games started from an initial position can be saved")
    return {
        "format": FORMAT,
        "version": VERSION,
        "metadata": {
            "variant": match.rules.name,
            "seeds_per_cup": seeds,
            "players": {p.name.lower(): specs[p] for p in Player},
            "saved_at": datetime.now(UTC).isoformat(),
        },
        "history": [move for _, move, _ in match.history],
        "state": _state_document(match.state),
    }


def from_document(document: object) -> tuple[Match, dict[Player, str]]:
    """Rebuild the match and player specs from a save document.

    Raises SaveError unless the document is well-formed, every move in its
    history replays legally, and the recorded state matches the replayed one.
    """
    doc = _mapping(document, "save document")
    if doc.get("format") != FORMAT:
        raise SaveError("not a mancala save document")
    if doc.get("version") != VERSION:
        raise SaveError(f"unsupported save version: {doc.get('version')!r}")
    metadata = _mapping(doc.get("metadata"), "metadata")
    _string(metadata.get("saved_at"), "saved_at")
    players = _mapping(metadata.get("players"), "players")
    specs = {p: _string(players.get(p.name.lower()), p.name.lower()) for p in Player}
    try:
        rules = variants.get(_string(metadata.get("variant"), "variant"))
        initial = rules.initial_state(
            _integer(metadata.get("seeds_per_cup"), "seeds_per_cup")
        )
    except ValueError as error:
        raise SaveError(str(error)) from error
    history = doc.get("history")
    if not isinstance(history, list):
        raise SaveError("history must be a list of moves")
    match = Match(rules, initial)
    for number, move in enumerate(history, start=1):
        try:
            match.play(_integer(move, f"history move {number}"))
        except IllegalMoveError as error:
            raise SaveError(
                f"history move {number} cannot be replayed: {error}"
            ) from error
    if doc.get("state") != _state_document(match.state):
        raise SaveError("recorded state does not match the state replayed from history")
    return match, specs


def _state_document(state: GameState) -> dict[str, object]:
    return {
        "board": [list(row) for row in state.board],
        "stores": list(state.stores),
        "current_player": state.current_player.name.lower(),
    }


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SaveError(f"{name} must be an object, got {value!r}")
    return cast(dict[str, object], value)


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise SaveError(f"{name} must be a string, got {value!r}")
    return value


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SaveError(f"{name} must be an integer, got {value!r}")
    return value
