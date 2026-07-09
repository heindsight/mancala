# Mancala Engine + CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resurrect the mancala project as a modern Python package: an immutable, UI-agnostic engine implementing Kalah and Oware, plus a terminal interface for hot-seat play.

**Architecture:** Immutable `GameState` values (NamedTuple) transformed by stateless per-variant `Rules` objects whose `apply_move` returns a fully resolved new state plus an event list; a thin stateful `Match` wrapper validates moves and threads state history (for Oware's repetition rule); the CLI renders states and narrates events. Spec: `docs/superpowers/specs/2026-07-09-mancala-resurrection-design.md`.

**Tech Stack:** Python 3.13+, uv (project + build), ruff (lint/format), ty (type check; mypy is the fallback), pytest + hypothesis. Zero runtime dependencies.

## Global Constraints

- `requires-python = ">=3.13"`; run everything through uv: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run ty check`.
- Zero runtime dependencies. Dev dependencies exactly: `pytest`, `hypothesis`, `ruff`, `ty`.
- Type checker is **ty**. If a ty beta bug blocks a task, switch the whole project to **mypy** (never pyright), note it in that task's commit message, and continue.
- All engine types are immutable. `GameState` and `MoveResult` are `typing.NamedTuple`. **Events are frozen dataclasses, not NamedTuples** — deliberate: several events have identical field shapes (`SeedStored(player)` vs `ExtraTurn(player)`), and NamedTuples of the same arity compare equal across types, which would silently weaken event-sequence assertions in tests. Frozen dataclass equality is type-sensitive.
- `apply_move` always returns a **fully resolved** state: sowing, captures, turn passing, and — if the move ended the game — the end-of-game sweep. Consequently, for both variants a state is terminal iff **every cup is empty**, and `is_over`/`winner` stay pure single-state functions.
- Cup indices are 0-based from each player's own perspective everywhere in the engine; the CLI presents them 1-based.
- Players are `Player.SOUTH` (moves first) and `Player.NORTH`.
- Commit after every task with plain imperative messages (repo style: "Add ancient mancala game code to version control" — no `feat:` prefixes).
- Tests are input/output driven; no mocks, no patching.

## File structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | uv-managed project: metadata, dev deps, console script, ruff/pytest config |
| `src/mancala/__init__.py` | package marker (docstring only) |
| `src/mancala/state.py` | `Player`, `GameState` |
| `src/mancala/events.py` | event dataclasses + `Event` union |
| `src/mancala/rules.py` | `Move`, `MoveResult`, `IllegalMoveError`, `Rules` protocol |
| `src/mancala/match.py` | stateful `Match` wrapper |
| `src/mancala/variants/__init__.py` | registry: `get(name)`, `available()` |
| `src/mancala/variants/_common.py` | helpers shared by variants (sweep, board helpers) |
| `src/mancala/variants/kalah.py` | Kalah rules |
| `src/mancala/variants/oware.py` | Oware rules |
| `src/mancala/cli.py` | argparse CLI: render, narrate, game loop, `main` |
| `tests/helpers.py` | `make_state` test helper |
| `tests/test_*.py` | one module per unit (see tasks) |
| `.github/workflows/ci.yml` | CI: ruff, ty, pytest |

---

### Task 1: Scaffold — remove ancient code, modern uv project

**Files:**
- Delete: `__init__.py`, `mancala.py`, `mancala_gtk.py`, `mancala_gtk.pyc`, `games/`, `uis/`
- Create: `pyproject.toml`, `.gitignore`, `README.md`, `src/mancala/__init__.py`, `tests/test_package.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: importable empty package `mancala`; `uv run pytest / ruff / ty` all work

- [ ] **Step 1: Remove the ancient code from the working tree** (git history preserves it)

```bash
git rm -r --quiet __init__.py mancala.py mancala_gtk.py mancala_gtk.pyc games uis
```

- [ ] **Step 2: Initialize the uv project**

```bash
uv init --lib --name mancala .
```

This creates `pyproject.toml`, `.python-version`, `src/mancala/__init__.py`, `src/mancala/py.typed`, and a stub `README.md`. If `uv init` refuses because files exist, pass `--no-readme` and/or remove the conflicting stub first — the end state matters, not the exact command.

- [ ] **Step 3: Add dev dependencies**

```bash
uv add --dev pytest hypothesis ruff ty
```

- [ ] **Step 4: Edit `pyproject.toml`** — keep the uv-generated `[build-system]` (uv_build) and `[dependency-groups]` sections; make the rest look like this:

```toml
[project]
name = "mancala"
version = "0.1.0"
description = "Mancala family board games: engine and terminal interface"
readme = "README.md"
requires-python = ">=3.13"
dependencies = []

[project.scripts]
mancala = "mancala.cli:main"

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]

[tool.ruff.lint.flake8-bugbear]
# frozenset() as a default argument (Rules.apply_move) is immutable and safe.
extend-immutable-calls = ["frozenset"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 5: Replace `src/mancala/__init__.py` content** (uv generates a sample function; remove it):

```python
"""Mancala family board games: engine and terminal interface."""
```

- [ ] **Step 6: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
.hypothesis/
.ruff_cache/
dist/
```

- [ ] **Step 7: Write `README.md`**

```markdown
# Mancala

Mancala family board games — a modern resurrection of an ancient student
project. Immutable game engine (Kalah and Oware) plus a terminal interface
for hot-seat play.

## Play

    uv run mancala --variant kalah Heinrich Nora

## Develop

    uv run pytest
    uv run ruff check .
    uv run ruff format .
    uv run ty check

Design docs live in `docs/superpowers/specs/`.
```

- [ ] **Step 8: Write the smoke test** `tests/test_package.py`:

```python
import mancala


def test_package_is_importable() -> None:
    assert mancala.__name__ == "mancala"
```

- [ ] **Step 9: Verify everything runs**

Run: `uv sync && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: pytest reports `1 passed`; ruff and ty report no errors. (The `mancala.cli` script target doesn't exist yet — that's fine, script resolution happens at invocation, not at sync.)

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "Replace ancient Python 2 code with modern uv project scaffold"
```

---

### Task 2: Core state types

**Files:**
- Create: `src/mancala/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: nothing
- Produces: `Player` (enum: `SOUTH = 0`, `NORTH = 1`; property `opponent -> Player`); `GameState(board: tuple[tuple[int, ...], tuple[int, ...]], stores: tuple[int, int], current_player: Player)` NamedTuple. `board[p.value]` is player p's cups in sowing order.

- [ ] **Step 1: Write the failing tests** `tests/test_state.py`:

```python
from mancala.state import GameState, Player


def test_opponent_is_the_other_player() -> None:
    assert Player.SOUTH.opponent is Player.NORTH
    assert Player.NORTH.opponent is Player.SOUTH


def test_game_state_is_hashable_and_value_equal() -> None:
    a = GameState(board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH)
    b = GameState(board=((4,) * 6, (4,) * 6), stores=(0, 0), current_player=Player.SOUTH)
    assert a == b
    assert hash(a) == hash(b)
    assert a in {b}


def test_board_is_indexed_by_player_value() -> None:
    state = GameState(board=((1, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 2)), stores=(3, 4),
                      current_player=Player.NORTH)
    assert state.board[Player.SOUTH.value] == (1, 0, 0, 0, 0, 0)
    assert state.board[Player.NORTH.value] == (0, 0, 0, 0, 0, 2)
    assert state.stores[Player.NORTH.value] == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mancala.state'`

- [ ] **Step 3: Implement** `src/mancala/state.py`:

```python
"""Immutable game state shared by all variants."""

from enum import Enum
from typing import NamedTuple


class Player(Enum):
    SOUTH = 0
    NORTH = 1

    @property
    def opponent(self) -> "Player":
        return Player(1 - self.value)


class GameState(NamedTuple):
    """A complete position. board[p.value] holds Player(p)'s cups in sowing order."""

    board: tuple[tuple[int, ...], tuple[int, ...]]
    stores: tuple[int, int]
    current_player: Player
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_state.py -v`
Expected: 3 passed

- [ ] **Step 5: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/state.py tests/test_state.py
git commit -m "Add Player and immutable GameState core types"
```

---

### Task 3: Events, Rules protocol, result types

**Files:**
- Create: `src/mancala/events.py`, `src/mancala/rules.py`
- Test: `tests/test_core_types.py`

**Interfaces:**
- Consumes: `Player`, `GameState` from `mancala.state`
- Produces:
  - `mancala.events`: frozen dataclasses `SeedSown(player: Player, cup: int)` (the cup's owner), `SeedStored(player: Player)`, `Captured(by: Player, owner: Player, cup: int, seeds: int)`, `ExtraTurn(player: Player)`, `GameOver(winner: Player | None)`; alias `type Event = SeedSown | SeedStored | Captured | ExtraTurn | GameOver`.
  - `mancala.rules`: `type Move = int`; `MoveResult(state: GameState, events: tuple[Event, ...])` NamedTuple; `IllegalMoveError(Exception)`; `Rules` Protocol with methods `initial_state(seeds_per_cup: int = 4) -> GameState`, `legal_moves(state) -> tuple[Move, ...]`, `apply_move(state, move, history: Container[GameState] = frozenset()) -> MoveResult`, `is_over(state) -> bool`, `winner(state) -> Player | None`.

- [ ] **Step 1: Write the failing tests** `tests/test_core_types.py`:

```python
from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.rules import IllegalMoveError, MoveResult
from mancala.state import GameState, Player


def test_same_shaped_events_of_different_types_are_not_equal() -> None:
    # This is why events are frozen dataclasses rather than NamedTuples.
    assert SeedStored(Player.SOUTH) != ExtraTurn(Player.SOUTH)
    assert GameOver(Player.SOUTH) != ExtraTurn(Player.SOUTH)


def test_events_are_value_equal_within_a_type() -> None:
    assert SeedSown(Player.NORTH, 3) == SeedSown(Player.NORTH, 3)
    assert Captured(by=Player.SOUTH, owner=Player.NORTH, cup=2, seeds=3) == Captured(
        by=Player.SOUTH, owner=Player.NORTH, cup=2, seeds=3
    )


def test_events_are_immutable() -> None:
    import dataclasses

    import pytest

    event = SeedSown(Player.SOUTH, 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.cup = 5  # type: ignore[misc]


def test_move_result_carries_state_and_events() -> None:
    state = GameState(board=((0,) * 6, (0,) * 6), stores=(24, 24), current_player=Player.SOUTH)
    result = MoveResult(state=state, events=(GameOver(None),))
    assert result.state is state
    assert result.events == (GameOver(None),)


def test_illegal_move_error_is_an_exception() -> None:
    assert issubclass(IllegalMoveError, Exception)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_core_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mancala.events'`

- [ ] **Step 3: Implement** `src/mancala/events.py`:

```python
"""Events narrate what happened during a move, in order, for consumers to replay."""

from dataclasses import dataclass

from mancala.state import Player


@dataclass(frozen=True, slots=True)
class SeedSown:
    """One seed dropped into `player`'s cup `cup`."""

    player: Player
    cup: int


@dataclass(frozen=True, slots=True)
class SeedStored:
    """One seed dropped into `player`'s store."""

    player: Player


@dataclass(frozen=True, slots=True)
class Captured:
    """`by` captured `seeds` seeds from `owner`'s cup `cup` into `by`'s store."""

    by: Player
    owner: Player
    cup: int
    seeds: int


@dataclass(frozen=True, slots=True)
class ExtraTurn:
    """`player` moves again."""

    player: Player


@dataclass(frozen=True, slots=True)
class GameOver:
    """The game ended; `winner` is None for a draw."""

    winner: Player | None


type Event = SeedSown | SeedStored | Captured | ExtraTurn | GameOver
```

- [ ] **Step 4: Implement** `src/mancala/rules.py`:

```python
"""The Rules protocol every variant implements, plus shared result types."""

from collections.abc import Container
from typing import NamedTuple, Protocol

from mancala.events import Event
from mancala.state import GameState, Player

type Move = int
"""A move is a 0-based cup index from the mover's own perspective."""


class MoveResult(NamedTuple):
    state: GameState
    events: tuple[Event, ...]


class IllegalMoveError(Exception):
    """The attempted move is not legal in the current state."""


class Rules(Protocol):
    """A stateless mancala variant.

    `apply_move` assumes the move is legal (validate via `Match`) and returns a
    fully resolved state: sowing, captures, turn passing, and the end-of-game
    sweep if the move ended the game. `history` holds the states already seen
    this game; variants with repetition rules (Oware) consult it, others
    ignore it. Terminal states have every cup empty, so `is_over` and
    `winner` are pure functions of a single state.
    """

    name: str

    def initial_state(self, seeds_per_cup: int = 4) -> GameState: ...

    def legal_moves(self, state: GameState) -> tuple[Move, ...]: ...

    def apply_move(
        self,
        state: GameState,
        move: Move,
        history: Container[GameState] = frozenset(),
    ) -> MoveResult: ...

    def is_over(self, state: GameState) -> bool: ...

    def winner(self, state: GameState) -> Player | None: ...
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_core_types.py -v`
Expected: 5 passed

- [ ] **Step 6: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/events.py src/mancala/rules.py tests/test_core_types.py
git commit -m "Add event types and the Rules protocol"
```

---
### Task 4: Kalah — setup and legal moves

**Files:**
- Create: `src/mancala/variants/__init__.py` (empty for now), `src/mancala/variants/_common.py`, `src/mancala/variants/kalah.py`, `tests/helpers.py`
- Test: `tests/test_kalah.py`

**Interfaces:**
- Consumes: `GameState`, `Player` from `mancala.state`; `Move` from `mancala.rules`
- Produces:
  - `mancala.variants._common.CUPS` (= 6)
  - `Kalah` class with `name = "kalah"`, `initial_state(seeds_per_cup: int = 4) -> GameState` (ValueError outside 3–6), `legal_moves(state) -> tuple[Move, ...]` (indices of the mover's non-empty cups)
  - `tests/helpers.py`: `make_state(south, north, stores=(0, 0), player=Player.SOUTH) -> GameState` — pytest puts `tests/` on `sys.path` (no `__init__.py` in tests), so test modules do `from helpers import make_state`.

- [ ] **Step 1: Write the test helper** `tests/helpers.py`:

```python
"""Shared test helpers."""

from mancala.state import GameState, Player


def make_state(
    south: tuple[int, ...],
    north: tuple[int, ...],
    stores: tuple[int, int] = (0, 0),
    player: Player = Player.SOUTH,
) -> GameState:
    return GameState(board=(south, north), stores=stores, current_player=player)
```

- [ ] **Step 2: Write the failing tests** `tests/test_kalah.py`:

```python
import pytest
from helpers import make_state

from mancala.state import Player
from mancala.variants.kalah import Kalah

KALAH = Kalah()


def test_initial_state_has_four_seeds_per_cup_by_default() -> None:
    state = KALAH.initial_state()
    assert state.board == ((4,) * 6, (4,) * 6)
    assert state.stores == (0, 0)
    assert state.current_player is Player.SOUTH


def test_initial_state_accepts_three_to_six_seeds() -> None:
    assert KALAH.initial_state(seeds_per_cup=3).board == ((3,) * 6, (3,) * 6)
    assert KALAH.initial_state(seeds_per_cup=6).board == ((6,) * 6, (6,) * 6)


@pytest.mark.parametrize("seeds", [0, 1, 2, 7, -1])
def test_initial_state_rejects_unsupported_seed_counts(seeds: int) -> None:
    with pytest.raises(ValueError, match="3-6"):
        KALAH.initial_state(seeds_per_cup=seeds)


def test_legal_moves_are_the_movers_nonempty_cups() -> None:
    state = make_state(south=(0, 3, 0, 1, 0, 2), north=(4, 4, 4, 4, 4, 4))
    assert KALAH.legal_moves(state) == (1, 3, 5)


def test_legal_moves_use_the_current_players_row() -> None:
    state = make_state(
        south=(1, 1, 1, 1, 1, 1), north=(0, 0, 5, 0, 0, 0), player=Player.NORTH
    )
    assert KALAH.legal_moves(state) == (2,)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_kalah.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mancala.variants'`

- [ ] **Step 4: Create the package and helpers**

`src/mancala/variants/__init__.py`:

```python
"""Game variant implementations."""
```

`src/mancala/variants/_common.py`:

```python
"""Helpers shared by variant implementations (internal)."""

CUPS = 6
```

- [ ] **Step 5: Implement** `src/mancala/variants/kalah.py`:

```python
"""Kalah: the classic store-and-capture mancala variant."""

from mancala.rules import Move
from mancala.state import GameState, Player
from mancala.variants._common import CUPS


class Kalah:
    name = "kalah"

    def initial_state(self, seeds_per_cup: int = 4) -> GameState:
        if not 3 <= seeds_per_cup <= 6:
            raise ValueError("kalah supports 3-6 seeds per cup")
        row = (seeds_per_cup,) * CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        own = state.board[state.current_player.value]
        return tuple(cup for cup, seeds in enumerate(own) if seeds)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_kalah.py -v`
Expected: 9 passed (the parametrized rejection test counts as 5)

- [ ] **Step 7: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/variants tests/helpers.py tests/test_kalah.py
git commit -m "Add Kalah setup and legal move generation"
```

---

### Task 5: Kalah — apply_move, endings, winner

**Files:**
- Modify: `src/mancala/variants/_common.py`, `src/mancala/variants/kalah.py`
- Test: `tests/test_kalah.py` (append)

**Interfaces:**
- Consumes: everything from Tasks 2–4
- Produces:
  - `_common`: `mutable(state) -> tuple[list[list[int]], list[int]]`, `frozen(board, stores, player) -> GameState`, `sweep_remaining(board, stores) -> list[Event]` (moves every remaining seed to its owner's store, emitting `Captured(by=owner, owner=owner, ...)`), `board_empty(state) -> bool`, `winner_from_stores(state) -> Player | None`
  - `Kalah.apply_move(state, move, history=frozenset()) -> MoveResult`, `Kalah.is_over(state) -> bool`, `Kalah.winner(state) -> Player | None`. Kalah ignores `history`.

Kalah rules implemented here (spec): counterclockwise sowing over a 13-position cycle (own cups 0–5, own store, opponent cups 0–5; opponent's store skipped); last seed in own store → extra turn; last seed making own cup exactly 1 with a non-empty opposite cup (opposite of own cup *i* is opponent cup *5−i*) → capture both cups to own store; if either row is empty after the move, sweep all remaining seeds to their owners and the game ends (a game-ending move grants no extra turn).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_kalah.py`:

```python
from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored


def test_simple_sow_distributes_counterclockwise_and_passes_turn() -> None:
    result = KALAH.apply_move(KALAH.initial_state(), 0)
    assert result.state.board[Player.SOUTH.value] == (0, 5, 5, 5, 5, 4)
    assert result.state.board[Player.NORTH.value] == (4, 4, 4, 4, 4, 4)
    assert result.state.stores == (0, 0)
    assert result.state.current_player is Player.NORTH
    assert result.events == (
        SeedSown(Player.SOUTH, 1),
        SeedSown(Player.SOUTH, 2),
        SeedSown(Player.SOUTH, 3),
        SeedSown(Player.SOUTH, 4),
    )


def test_last_seed_in_store_grants_extra_turn() -> None:
    result = KALAH.apply_move(KALAH.initial_state(), 2)
    assert result.state.board[Player.SOUTH.value] == (4, 4, 0, 5, 5, 5)
    assert result.state.stores == (1, 0)
    assert result.state.current_player is Player.SOUTH
    assert result.events == (
        SeedSown(Player.SOUTH, 3),
        SeedSown(Player.SOUTH, 4),
        SeedSown(Player.SOUTH, 5),
        SeedStored(Player.SOUTH),
        ExtraTurn(Player.SOUTH),
    )


def test_sowing_skips_the_opponents_store() -> None:
    # 9 seeds from south cup 5: own store, all six north cups, then own cups 0-1.
    state = make_state(south=(1, 1, 1, 0, 0, 9), north=(0, 0, 1, 0, 0, 0))
    result = KALAH.apply_move(state, 5)
    assert result.state.board[Player.SOUTH.value] == (2, 2, 1, 0, 0, 0)
    assert result.state.board[Player.NORTH.value] == (1, 1, 2, 1, 1, 1)
    assert result.state.stores == (1, 0)  # north's store untouched
    assert result.state.current_player is Player.NORTH


def test_last_seed_in_own_empty_cup_captures_opposite() -> None:
    state = make_state(south=(1, 0, 2, 0, 0, 1), north=(0, 0, 0, 0, 3, 2))
    result = KALAH.apply_move(state, 0)
    # South's seed lands in own empty cup 1; opposite is north cup 4 (3 seeds).
    assert result.state.board[Player.SOUTH.value] == (0, 0, 2, 0, 0, 1)
    assert result.state.board[Player.NORTH.value] == (0, 0, 0, 0, 0, 2)
    assert result.state.stores == (4, 0)
    assert result.state.current_player is Player.NORTH
    assert result.events == (
        SeedSown(Player.SOUTH, 1),
        Captured(by=Player.SOUTH, owner=Player.SOUTH, cup=1, seeds=1),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=4, seeds=3),
    )


def test_no_capture_when_opposite_cup_is_empty() -> None:
    state = make_state(south=(1, 0, 2, 0, 0, 1), north=(0, 0, 0, 0, 0, 2))
    result = KALAH.apply_move(state, 0)
    assert result.state.board[Player.SOUTH.value] == (0, 1, 2, 0, 0, 1)
    assert result.state.stores == (0, 0)
    assert not any(isinstance(e, Captured) for e in result.events)


def test_emptying_your_row_ends_the_game_and_sweeps() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 1), north=(2, 0, 0, 0, 0, 3), stores=(20, 22))
    result = KALAH.apply_move(state, 5)  # last seed lands in south's store
    assert result.state.board == ((0,) * 6, (0,) * 6)
    assert result.state.stores == (21, 27)
    assert not any(isinstance(e, ExtraTurn) for e in result.events)  # game end trumps extra turn
    assert result.events[-3:] == (
        Captured(by=Player.NORTH, owner=Player.NORTH, cup=0, seeds=2),
        Captured(by=Player.NORTH, owner=Player.NORTH, cup=5, seeds=3),
        GameOver(Player.NORTH),
    )
    assert KALAH.is_over(result.state)
    assert KALAH.winner(result.state) is Player.NORTH


def test_equal_stores_after_sweep_is_a_draw() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 1), north=(0, 0, 0, 0, 0, 1), stores=(23, 23))
    result = KALAH.apply_move(state, 5)
    assert result.state.stores == (24, 24)
    assert result.events[-1] == GameOver(None)
    assert KALAH.winner(result.state) is None


def test_ongoing_game_is_not_over_and_has_no_winner() -> None:
    state = KALAH.initial_state()
    assert not KALAH.is_over(state)
    assert KALAH.winner(state) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_kalah.py -v`
Expected: new tests FAIL — `AttributeError: 'Kalah' object has no attribute 'apply_move'`

- [ ] **Step 3: Extend** `src/mancala/variants/_common.py` to:

```python
"""Helpers shared by variant implementations (internal)."""

from mancala.events import Captured, Event
from mancala.state import GameState, Player

CUPS = 6


def mutable(state: GameState) -> tuple[list[list[int]], list[int]]:
    """Working copies of the board and stores for building the next state."""
    return [list(row) for row in state.board], list(state.stores)


def frozen(board: list[list[int]], stores: list[int], player: Player) -> GameState:
    return GameState(
        board=(tuple(board[0]), tuple(board[1])),
        stores=(stores[0], stores[1]),
        current_player=player,
    )


def sweep_remaining(board: list[list[int]], stores: list[int]) -> list[Event]:
    """Move every seed left on each side to its owner's store."""
    events: list[Event] = []
    for player in Player:
        for cup, seeds in enumerate(board[player.value]):
            if seeds:
                stores[player.value] += seeds
                board[player.value][cup] = 0
                events.append(Captured(by=player, owner=player, cup=cup, seeds=seeds))
    return events


def board_empty(state: GameState) -> bool:
    return not any(state.board[0]) and not any(state.board[1])


def winner_from_stores(state: GameState) -> Player | None:
    south, north = state.stores
    if south > north:
        return Player.SOUTH
    if north > south:
        return Player.NORTH
    return None
```

- [ ] **Step 4: Complete** `src/mancala/variants/kalah.py`:

```python
"""Kalah: the classic store-and-capture mancala variant."""

from collections.abc import Container

from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.rules import Move, MoveResult
from mancala.state import GameState, Player
from mancala.variants._common import (
    CUPS,
    board_empty,
    frozen,
    mutable,
    sweep_remaining,
    winner_from_stores,
)

# Sowing cycle: positions 0-5 are the mover's cups, 6 the mover's store,
# 7-12 the opponent's cups. The opponent's store is not part of the cycle.
_CYCLE = 13
_STORE = CUPS


class Kalah:
    name = "kalah"

    def initial_state(self, seeds_per_cup: int = 4) -> GameState:
        if not 3 <= seeds_per_cup <= 6:
            raise ValueError("kalah supports 3-6 seeds per cup")
        row = (seeds_per_cup,) * CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        own = state.board[state.current_player.value]
        return tuple(cup for cup, seeds in enumerate(own) if seeds)

    def apply_move(
        self,
        state: GameState,
        move: Move,
        history: Container[GameState] = frozenset(),
    ) -> MoveResult:
        mover = state.current_player
        opponent = mover.opponent
        board, stores = mutable(state)
        events: list[Event] = []

        seeds = board[mover.value][move]
        board[mover.value][move] = 0
        pos = move
        while seeds:
            pos = (pos + 1) % _CYCLE
            if pos == _STORE:
                stores[mover.value] += 1
                events.append(SeedStored(mover))
            else:
                owner, cup = (mover, pos) if pos < CUPS else (opponent, pos - CUPS - 1)
                board[owner.value][cup] += 1
                events.append(SeedSown(owner, cup))
            seeds -= 1

        opposite = CUPS - 1 - pos
        if pos < CUPS and board[mover.value][pos] == 1 and board[opponent.value][opposite]:
            for owner, cup in ((mover, pos), (opponent, opposite)):
                taken = board[owner.value][cup]
                stores[mover.value] += taken
                board[owner.value][cup] = 0
                events.append(Captured(by=mover, owner=owner, cup=cup, seeds=taken))

        if not any(board[0]) or not any(board[1]):
            events.extend(sweep_remaining(board, stores))
            final = frozen(board, stores, opponent)
            events.append(GameOver(winner_from_stores(final)))
            return MoveResult(final, tuple(events))

        if pos == _STORE:
            events.append(ExtraTurn(mover))
            return MoveResult(frozen(board, stores, mover), tuple(events))

        return MoveResult(frozen(board, stores, opponent), tuple(events))

    def is_over(self, state: GameState) -> bool:
        return board_empty(state)

    def winner(self, state: GameState) -> Player | None:
        return winner_from_stores(state) if self.is_over(state) else None
```

Note: `opposite` is computed before the guard, so when `pos` is in the opponent's row it is meaningless — the `pos < CUPS` check short-circuits first.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_kalah.py -v`
Expected: 17 passed

- [ ] **Step 6: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/variants tests/test_kalah.py
git commit -m "Implement Kalah sowing, capture, extra turn, and game end"
```

---

### Task 6: Match wrapper

**Files:**
- Create: `src/mancala/match.py`
- Test: `tests/test_match.py`

**Interfaces:**
- Consumes: `Rules` protocol, `Kalah` (for tests), `IllegalMoveError`, `MoveResult`
- Produces: `Match(rules: Rules, state: GameState | None = None)` — `state=None` means `rules.initial_state()`. Members: `rules`, property `state -> GameState`, property `history -> tuple[tuple[GameState, Move, tuple[Event, ...]], ...]` (state *before* each move), property `is_over -> bool`, property `winner -> Player | None`, method `play(move: Move) -> MoveResult` (raises `IllegalMoveError` on illegal move or finished game; threads the set of seen states into `apply_move`). `__init__` raises `ValueError` for an *unresolved* state — one with no legal moves that is not over (engine functions assume states produced by `initial_state`/`apply_move`; rejecting hand-built unswept positions early prevents a deadlocked match).

- [ ] **Step 1: Write the failing tests** `tests/test_match.py`:

```python
import pytest
from helpers import make_state

from mancala.match import Match
from mancala.rules import IllegalMoveError
from mancala.state import Player
from mancala.variants.kalah import Kalah

KALAH = Kalah()


def test_match_starts_from_the_initial_state_by_default() -> None:
    match = Match(KALAH)
    assert match.state == KALAH.initial_state()
    assert match.history == ()
    assert not match.is_over
    assert match.winner is None


def test_play_advances_the_state_and_records_history() -> None:
    match = Match(KALAH)
    before = match.state
    result = match.play(0)
    assert match.state == result.state
    assert match.state != before
    assert match.history == ((before, 0, result.events),)


def test_playing_an_empty_cup_is_illegal() -> None:
    match = Match(KALAH, make_state(south=(0, 4, 0, 0, 0, 0), north=(1, 1, 1, 1, 1, 1)))
    with pytest.raises(IllegalMoveError, match="cup 1"):
        match.play(0)


@pytest.mark.parametrize("move", [-1, 6, 99])
def test_out_of_range_moves_are_illegal(move: int) -> None:
    match = Match(KALAH)
    with pytest.raises(IllegalMoveError):
        match.play(move)


def test_playing_after_the_game_is_over_is_illegal() -> None:
    match = Match(KALAH, make_state(south=(0,) * 6, north=(0,) * 6, stores=(25, 23)))
    assert match.is_over
    assert match.winner is Player.SOUTH
    with pytest.raises(IllegalMoveError, match="over"):
        match.play(0)


def test_an_illegal_move_leaves_the_match_unchanged() -> None:
    match = Match(KALAH)
    before = match.state
    with pytest.raises(IllegalMoveError):
        match.play(-1)
    assert match.state == before
    assert match.history == ()


def test_unresolved_states_are_rejected() -> None:
    # South's row is empty but was never swept: no legal moves, yet not
    # "over". apply_move never produces such states; reject them up front.
    unswept = make_state(south=(0,) * 6, north=(1, 1, 1, 1, 1, 1), stores=(20, 22))
    with pytest.raises(ValueError, match="unresolved"):
        Match(KALAH, unswept)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_match.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mancala.match'`

- [ ] **Step 3: Implement** `src/mancala/match.py`:

```python
"""Stateful wrapper around a Rules implementation for interactive play."""

from mancala.events import Event
from mancala.rules import IllegalMoveError, Move, MoveResult, Rules
from mancala.state import GameState, Player


class Match:
    """Holds the current state of one game and validates moves.

    Also threads the set of previously seen states into `Rules.apply_move`,
    which is how variants with repetition rules (Oware) detect cycles — so
    every game played through Match terminates.
    """

    def __init__(self, rules: Rules, state: GameState | None = None) -> None:
        self.rules = rules
        self._state = state if state is not None else rules.initial_state()
        if not rules.is_over(self._state) and not rules.legal_moves(self._state):
            raise ValueError(
                "unresolved state: no legal moves but not over; "
                "pass states produced by initial_state or apply_move"
            )
        self._seen: set[GameState] = {self._state}
        self._history: list[tuple[GameState, Move, tuple[Event, ...]]] = []

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def history(self) -> tuple[tuple[GameState, Move, tuple[Event, ...]], ...]:
        return tuple(self._history)

    @property
    def is_over(self) -> bool:
        return self.rules.is_over(self._state)

    @property
    def winner(self) -> Player | None:
        return self.rules.winner(self._state)

    def play(self, move: Move) -> MoveResult:
        if self.is_over:
            raise IllegalMoveError("the game is over")
        if move not in self.rules.legal_moves(self._state):
            raise IllegalMoveError(f"cup {move + 1} is not a legal move")
        result = self.rules.apply_move(self._state, move, self._seen)
        self._history.append((self._state, move, result.events))
        self._state = result.state
        self._seen.add(result.state)
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_match.py -v`
Expected: 9 passed

- [ ] **Step 5: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/match.py tests/test_match.py
git commit -m "Add Match wrapper validating moves and threading state history"
```

---
### Task 7: Oware — setup and legal moves (must-feed)

**Files:**
- Create: `src/mancala/variants/oware.py`
- Test: `tests/test_oware.py`

**Interfaces:**
- Consumes: `CUPS` from `_common`; `GameState`, `Player`, `Move`
- Produces: `Oware` class with `name = "oware"`, `initial_state(seeds_per_cup: int = 4)` (ValueError unless exactly 4), `legal_moves(state)`: non-empty own cups; when the opponent's row is empty, only moves that reach it (`cup + seeds >= 6`) — possibly `()`.

- [ ] **Step 1: Write the failing tests** `tests/test_oware.py`:

```python
import pytest
from helpers import make_state

from mancala.state import Player
from mancala.variants.oware import Oware

OWARE = Oware()


def test_initial_state_is_six_cups_of_four() -> None:
    state = OWARE.initial_state()
    assert state.board == ((4,) * 6, (4,) * 6)
    assert state.stores == (0, 0)
    assert state.current_player is Player.SOUTH


@pytest.mark.parametrize("seeds", [3, 5, 6])
def test_initial_state_rejects_anything_but_four_seeds(seeds: int) -> None:
    with pytest.raises(ValueError, match="4 seeds"):
        OWARE.initial_state(seeds_per_cup=seeds)


def test_legal_moves_are_the_movers_nonempty_cups() -> None:
    state = make_state(south=(0, 2, 0, 0, 1, 0), north=(4, 4, 4, 4, 4, 4))
    assert OWARE.legal_moves(state) == (1, 4)


def test_starved_opponent_restricts_moves_to_feeding_ones() -> None:
    # North is empty: south cup 0 (1 seed reaches cup 1 only) cannot feed;
    # cup 5 (3 seeds reach north cups 0-2) can.
    state = make_state(south=(1, 0, 0, 0, 0, 3), north=(0,) * 6)
    assert OWARE.legal_moves(state) == (5,)


def test_no_legal_moves_when_starved_opponent_cannot_be_fed() -> None:
    state = make_state(south=(1, 1, 0, 0, 0, 0), north=(0,) * 6)
    assert OWARE.legal_moves(state) == ()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_oware.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mancala.variants.oware'`

- [ ] **Step 3: Implement** `src/mancala/variants/oware.py`:

```python
"""Oware (Abapa rules): capture-by-twos-and-threes mancala."""

from mancala.rules import Move
from mancala.state import GameState, Player
from mancala.variants._common import CUPS


class Oware:
    name = "oware"

    def initial_state(self, seeds_per_cup: int = 4) -> GameState:
        if seeds_per_cup != 4:
            raise ValueError("oware is played with exactly 4 seeds per cup")
        row = (seeds_per_cup,) * CUPS
        return GameState(board=(row, row), stores=(0, 0), current_player=Player.SOUTH)

    def legal_moves(self, state: GameState) -> tuple[Move, ...]:
        mover = state.current_player
        own = state.board[mover.value]
        moves = tuple(cup for cup, seeds in enumerate(own) if seeds)
        if any(state.board[mover.opponent.value]):
            return moves
        # Opponent is out of seeds: only a move that reaches their row feeds them.
        return tuple(cup for cup in moves if cup + own[cup] >= CUPS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_oware.py -v`
Expected: 7 passed

- [ ] **Step 5: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/variants/oware.py tests/test_oware.py
git commit -m "Add Oware setup and legal moves with the must-feed rule"
```

---

### Task 8: Oware — sowing and captures (grand slam)

**Files:**
- Modify: `src/mancala/variants/oware.py`
- Test: `tests/test_oware.py` (append)

**Interfaces:**
- Consumes: `_common` helpers from Task 5
- Produces: `Oware.apply_move(state, move, history=frozenset()) -> MoveResult` — sowing and captures only; **game-ending detection is added in Task 9** (this task's version always returns the candidate next state with the turn passed).

Oware rules implemented here (spec): counterclockwise sowing over a 12-position cycle (own cups 0–5, opponent cups 0–5; no stores in the cycle); the origin cup is skipped (relevant when sowing 12+ seeds); if the last seed lands in an opponent cup leaving it at 2 or 3, capture it and chain backward through contiguous opponent cups holding 2 or 3 (the chain can only pass through cups sown this move, since sowing enters the opponent row at cup 0); a capture that would take *all* the opponent's seeds (grand slam) is legal but forfeited entirely. Oware has no extra turns and never emits `SeedStored` (seeds reach stores only via `Captured`).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_oware.py`:

```python
from mancala.events import Captured, SeedSown


def test_sowing_crosses_into_the_opponents_row() -> None:
    state = make_state(south=(0, 0, 0, 4, 0, 0), north=(4, 4, 4, 4, 4, 4))
    result = OWARE.apply_move(state, 3)
    assert result.state.board[Player.SOUTH.value] == (0, 0, 0, 0, 1, 1)
    assert result.state.board[Player.NORTH.value] == (5, 5, 4, 4, 4, 4)
    assert result.state.stores == (0, 0)
    assert result.state.current_player is Player.NORTH
    assert result.events == (
        SeedSown(Player.SOUTH, 4),
        SeedSown(Player.SOUTH, 5),
        SeedSown(Player.NORTH, 0),
        SeedSown(Player.NORTH, 1),
    )


def test_twelve_or_more_seeds_skip_the_origin_cup() -> None:
    state = make_state(south=(12, 0, 0, 0, 0, 0), north=(1, 1, 1, 1, 1, 1))
    result = OWARE.apply_move(state, 0)
    # 11 seeds fill own cups 1-5 and all north cups; the 12th skips the
    # origin and lands in own cup 1.
    assert result.state.board[Player.SOUTH.value] == (0, 2, 1, 1, 1, 1)
    assert result.state.board[Player.NORTH.value] == (2, 2, 2, 2, 2, 2)
    assert SeedSown(Player.SOUTH, 0) not in result.events


def test_capture_chains_backward_through_twos_and_threes() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 3), north=(1, 1, 1, 1, 1, 1))
    result = OWARE.apply_move(state, 5)
    # Seeds land in north cups 0-2, making each 2; all three are captured,
    # landing cup first.
    assert result.state.board[Player.NORTH.value] == (0, 0, 0, 1, 1, 1)
    assert result.state.stores == (6, 0)
    assert result.events[-3:] == (
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=2, seeds=2),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=1, seeds=2),
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=0, seeds=2),
    )


def test_capture_chain_stops_at_a_cup_not_holding_two_or_three() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 4), north=(1, 1, 4, 1, 0, 0))
    result = OWARE.apply_move(state, 5)
    # Landing cup is north 3 (now 2): captured. North 2 holds 5: chain stops.
    assert result.state.board[Player.NORTH.value] == (2, 2, 5, 0, 0, 0)
    assert result.state.stores == (2, 0)
    assert [e for e in result.events if isinstance(e, Captured)] == [
        Captured(by=Player.SOUTH, owner=Player.NORTH, cup=3, seeds=2)
    ]


def test_landing_in_your_own_row_never_captures() -> None:
    state = make_state(south=(2, 0, 3, 0, 0, 0), north=(1, 2, 0, 0, 0, 0))
    result = OWARE.apply_move(state, 0)  # lands in own cup 2
    assert result.state.stores == (0, 0)
    assert not any(isinstance(e, Captured) for e in result.events)


def test_grand_slam_capture_is_forfeited() -> None:
    state = make_state(south=(1, 0, 0, 0, 0, 2), north=(1, 1, 0, 0, 0, 0))
    result = OWARE.apply_move(state, 5)
    # The chain (north cups 1 and 0, both at 2) would take all north's seeds.
    assert result.state.board[Player.NORTH.value] == (2, 2, 0, 0, 0, 0)
    assert result.state.stores == (0, 0)
    assert not any(isinstance(e, Captured) for e in result.events)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_oware.py -v`
Expected: new tests FAIL — `AttributeError: 'Oware' object has no attribute 'apply_move'`

- [ ] **Step 3: Add `apply_move` to `src/mancala/variants/oware.py`** (imports shown; merge with the existing ones):

```python
from collections.abc import Container

from mancala.events import Captured, Event, SeedSown
from mancala.rules import Move, MoveResult
from mancala.state import GameState, Player
from mancala.variants._common import CUPS, frozen, mutable

# Sowing cycle: positions 0-5 are the mover's cups, 6-11 the opponent's.
_CYCLE = 2 * CUPS
```

```python
    def apply_move(
        self,
        state: GameState,
        move: Move,
        history: Container[GameState] = frozenset(),
    ) -> MoveResult:
        mover = state.current_player
        opponent = mover.opponent
        board, stores = mutable(state)
        events: list[Event] = []

        seeds = board[mover.value][move]
        board[mover.value][move] = 0
        pos = move
        while seeds:
            pos = (pos + 1) % _CYCLE
            if pos == move:  # the origin cup is never resown
                continue
            owner, cup = (mover, pos) if pos < CUPS else (opponent, pos - CUPS)
            board[owner.value][cup] += 1
            events.append(SeedSown(owner, cup))
            seeds -= 1

        if pos >= CUPS:  # landed in the opponent's row: try to capture
            chain: list[int] = []
            p = pos
            while p >= CUPS and board[opponent.value][p - CUPS] in (2, 3):
                chain.append(p - CUPS)
                p -= 1
            taking = sum(board[opponent.value][cup] for cup in chain)
            if chain and taking < sum(board[opponent.value]):  # grand slam forfeits
                for cup in chain:
                    taken = board[opponent.value][cup]
                    stores[mover.value] += taken
                    board[opponent.value][cup] = 0
                    events.append(Captured(by=mover, owner=opponent, cup=cup, seeds=taken))

        return MoveResult(frozen(board, stores, opponent), tuple(events))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_oware.py -v`
Expected: 13 passed

- [ ] **Step 5: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/variants/oware.py tests/test_oware.py
git commit -m "Implement Oware sowing and captures with the grand slam rule"
```

---

### Task 9: Oware — game endings (25+ seeds, starvation, repetition)

**Files:**
- Modify: `src/mancala/variants/oware.py`
- Test: `tests/test_oware.py` (append)

**Interfaces:**
- Consumes: `Match` (Task 6) for the repetition test; `sweep_remaining`, `board_empty`, `winner_from_stores` from `_common`
- Produces: complete `Oware` satisfying the `Rules` protocol: `apply_move` now ends the game (sweeping each side's remaining seeds to its owner, then `GameOver`) when any of these hold after a move — the mover's store exceeds 24; the next player has no legal move (row empty, or starved opponent unfeedable); the candidate state already occurred (is in `history`). Plus `is_over(state) -> bool` (board empty) and `winner(state) -> Player | None`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_oware.py`:

```python
from mancala.events import GameOver
from mancala.match import Match


def test_capturing_more_than_half_the_seeds_ends_the_game() -> None:
    state = make_state(south=(0, 0, 0, 0, 0, 1), north=(1, 1, 1, 1, 1, 1), stores=(23, 18))
    result = OWARE.apply_move(state, 5)
    # South captures north cup 0 (now 2): store reaches 25 (> 24). Game over;
    # north's remaining 5 seeds are swept to north's store.
    assert result.state.board == ((0,) * 6, (0,) * 6)
    assert result.state.stores == (25, 23)
    assert result.events[-1] == GameOver(Player.SOUTH)
    assert OWARE.is_over(result.state)
    assert OWARE.winner(result.state) is Player.SOUTH


def test_unfeedable_starved_opponent_ends_the_game() -> None:
    # North moves its last seed into south's row; south then cannot feed the
    # now-empty north (cup 0: 4 seeds reach only cup 4; cup 1: 1 seed).
    state = make_state(
        south=(3, 1, 0, 0, 0, 0), north=(0, 0, 0, 0, 0, 1), stores=(20, 23),
        player=Player.NORTH,
    )
    result = OWARE.apply_move(state, 5)
    assert result.state.board == ((0,) * 6, (0,) * 6)
    assert result.state.stores == (25, 23)  # south keeps its remaining 5 seeds
    assert result.events[-1] == GameOver(Player.SOUTH)


def test_repeated_position_ends_the_game_with_a_split() -> None:
    # Two lone seeds chase each other around the board and return to the
    # exact starting position (same player to move) after 12 moves.
    start = make_state(south=(0, 0, 0, 0, 0, 1), north=(0, 0, 0, 0, 0, 1), stores=(23, 23))
    match = Match(OWARE, start)
    for move in [5, 5, 0, 0, 1, 1, 2, 2, 3, 3, 4]:
        match.play(move)
        assert not match.is_over
    result = match.play(4)  # recreates the starting position
    assert match.is_over
    assert match.state.stores == (24, 24)  # each side keeps its own seed
    assert match.winner is None
    assert result.events[-1] == GameOver(None)


def test_ongoing_game_is_not_over() -> None:
    assert not OWARE.is_over(OWARE.initial_state())
    assert OWARE.winner(OWARE.initial_state()) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_oware.py -v`
Expected: new tests FAIL — `AttributeError: 'Oware' object has no attribute 'is_over'` (and the ending tests fail on unswept boards)

- [ ] **Step 3: Complete `src/mancala/variants/oware.py`.** Extend the `_common` import to include `board_empty`, `sweep_remaining`, `winner_from_stores`, and the events import to include `GameOver`. Add below `_CYCLE`:

```python
_TARGET = 24  # capturing more than half of the 48 seeds wins
```

Replace `apply_move`'s final `return` with:

```python
        candidate = frozen(board, stores, opponent)
        game_over = (
            stores[mover.value] > _TARGET
            or not self.legal_moves(candidate)
            or candidate in history
        )
        if game_over:
            events.extend(sweep_remaining(board, stores))
            final = frozen(board, stores, opponent)
            events.append(GameOver(winner_from_stores(final)))
            return MoveResult(final, tuple(events))

        return MoveResult(candidate, tuple(events))
```

And add the two protocol methods:

```python
    def is_over(self, state: GameState) -> bool:
        return board_empty(state)

    def winner(self, state: GameState) -> Player | None:
        return winner_from_stores(state) if self.is_over(state) else None
```

Note: `not self.legal_moves(candidate)` covers both starvation cases — the next player's row is empty, or their starved opponent cannot be fed. Starvation is resolved one ply early, inside the *previous* player's `apply_move`: the spec's "the mover keeps all remaining seeds" refers to the **next** player (the one facing the starved opponent), and since all remaining seeds sit on that player's side, sweeping each side to its owner awards them correctly.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_oware.py -v`
Expected: 17 passed

- [ ] **Step 5: Run the full suite, lint, type-check, commit**

```bash
uv run pytest && uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/variants/oware.py tests/test_oware.py
git commit -m "Implement Oware game endings: majority, starvation, repetition"
```

---

### Task 10: Variant registry

**Files:**
- Modify: `src/mancala/variants/__init__.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `Kalah`, `Oware`, `Rules`
- Produces: `mancala.variants.get(name: str) -> Rules` (ValueError with available names for unknown), `mancala.variants.available() -> tuple[str, ...]` (sorted).

- [ ] **Step 1: Write the failing tests** `tests/test_registry.py`:

```python
import pytest

from mancala import variants


def test_available_lists_both_variants_sorted() -> None:
    assert variants.available() == ("kalah", "oware")


def test_get_returns_the_named_variant() -> None:
    assert variants.get("kalah").name == "kalah"
    assert variants.get("oware").name == "oware"


def test_get_rejects_unknown_variants() -> None:
    with pytest.raises(ValueError, match="kalah, oware"):
        variants.get("senet")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL — `AttributeError: module 'mancala.variants' has no attribute 'available'`

- [ ] **Step 3: Implement** `src/mancala/variants/__init__.py`:

```python
"""Game variant implementations and their registry."""

from mancala.rules import Rules
from mancala.variants.kalah import Kalah
from mancala.variants.oware import Oware

_REGISTRY: dict[str, Rules] = {rules.name: rules for rules in (Kalah(), Oware())}


def get(name: str) -> Rules:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown variant {name!r}; available: {', '.join(available())}"
        ) from None


def available() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: 3 passed

- [ ] **Step 5: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/variants/__init__.py tests/test_registry.py
git commit -m "Add variant registry"
```

---
### Task 11: Full-game scripts and hypothesis properties

**Files:**
- Test: `tests/test_full_games.py`, `tests/test_properties.py`

**Interfaces:**
- Consumes: `Match`, `variants.get`, `variants.available`, event types
- Produces: nothing new — integration confidence. These tests exercise rule *interactions* that single-move unit tests miss.

- [ ] **Step 1: Write the full-game script tests** `tests/test_full_games.py` (these should pass immediately — they verify integration, not new code):

```python
from helpers import make_state

from mancala import variants
from mancala.events import GameOver
from mancala.match import Match
from mancala.state import Player


def test_scripted_kalah_endgame_plays_out_to_a_north_win() -> None:
    # Hand-verified script: south empties its row on the third move.
    start = make_state(south=(0, 0, 0, 0, 1, 2), north=(1, 0, 0, 0, 0, 1), stores=(20, 23))
    match = Match(variants.get("kalah"), start)

    match.play(4)  # south: 1 seed to cup 5 (now 3 seeds)
    assert match.state.board[Player.SOUTH.value] == (0, 0, 0, 0, 0, 3)
    assert not match.is_over

    match.play(0)  # north: 1 seed to own empty cup 1; opposite south cup 4 is empty -> no capture
    assert match.state.board[Player.NORTH.value] == (0, 1, 0, 0, 0, 1)
    assert match.state.stores == (20, 23)

    result = match.play(5)  # south: store, north cups 0-1; south's row is now empty
    assert match.is_over
    assert match.state.board == ((0,) * 6, (0,) * 6)
    assert match.state.stores == (21, 27)
    assert match.winner is Player.NORTH
    assert result.events[-1] == GameOver(Player.NORTH)


def first_legal_playout(name: str) -> Match:
    match = Match(variants.get(name))
    plies = 0
    while not match.is_over:
        match.play(match.rules.legal_moves(match.state)[0])
        plies += 1
        assert plies < 10_000, "playout did not terminate"
    return match


def test_kalah_first_legal_playout_terminates_and_conserves_seeds() -> None:
    match = first_legal_playout("kalah")
    assert sum(match.state.stores) == 48
    assert match.state.board == ((0,) * 6, (0,) * 6)


def test_oware_first_legal_playout_terminates_and_conserves_seeds() -> None:
    match = first_legal_playout("oware")
    assert sum(match.state.stores) == 48
    assert match.state.board == ((0,) * 6, (0,) * 6)
```

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/test_full_games.py -v`
Expected: 3 passed. If a playout fails, that is a real rules bug found by integration — debug the variant, don't loosen the test.

- [ ] **Step 3: Write the property tests** `tests/test_properties.py`:

```python
from hypothesis import given, settings
from hypothesis import strategies as st

from mancala import variants
from mancala.events import Captured, SeedSown
from mancala.match import Match
from mancala.state import Player


@settings(deadline=None)
@given(
    name=st.sampled_from(["kalah", "oware"]),
    seeds_per_cup=st.sampled_from([3, 4, 5, 6]),
    data=st.data(),
)
def test_random_playout_invariants(name: str, seeds_per_cup: int, data: st.DataObject) -> None:
    rules = variants.get(name)
    if name != "kalah":
        seeds_per_cup = 4
    match = Match(rules, rules.initial_state(seeds_per_cup))
    total = 2 * 6 * seeds_per_cup

    for _ in range(200):
        if match.is_over:
            break
        moves = rules.legal_moves(match.state)
        assert moves, "a non-terminal state must have legal moves"
        result = match.play(data.draw(st.sampled_from(moves)))

        state = result.state
        assert all(seeds >= 0 for row in state.board for seeds in row)
        assert sum(state.stores) + sum(sum(row) for row in state.board) == total
        for event in result.events:
            if isinstance(event, SeedSown | Captured):
                assert 0 <= event.cup < 6

    if match.is_over:
        assert rules.legal_moves(match.state) == ()
        assert match.state.board == ((0,) * 6, (0,) * 6)
        assert sum(match.state.stores) == total
        south, north = match.state.stores
        expected = (
            None if south == north else Player.SOUTH if south > north else Player.NORTH
        )
        assert match.winner is expected
```

- [ ] **Step 4: Run the property tests**

Run: `uv run pytest tests/test_properties.py -v`
Expected: 1 passed (hypothesis runs 100 examples inside it). Any failure comes with a shrunk counterexample — treat it as a rules bug.

- [ ] **Step 5: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add tests/test_full_games.py tests/test_properties.py
git commit -m "Add full-game scripts and hypothesis playout invariants"
```

---

### Task 12: CLI — rendering and narration (pure functions)

**Files:**
- Create: `src/mancala/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `GameState`, `Player`, event types
- Produces (all consumed by Task 13's game loop):
  - `render_board(state: GameState, names: dict[Player, str]) -> str` — current player's row on the bottom, cups labelled 1–6 left-to-right in sowing order; opponent's row on top, labelled right-to-left (counterclockwise flow); no trailing whitespace on any line.
  - `describe_move(mover: Player, move: int, events: tuple[Event, ...], names: dict[Player, str]) -> list[str]` — one summary line ("X sows N seeds from cup M."), then a line per capture / extra turn / game over.
  - `describe_result(state: GameState, winner: Player | None, names: dict[Player, str]) -> str`

- [ ] **Step 1: Write the failing tests** `tests/test_cli.py`:

```python
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
        south=(1, 2, 3, 4, 5, 6), north=(0, 0, 0, 0, 0, 0), stores=(3, 9),
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mancala.cli'`

- [ ] **Step 3: Implement the pure functions in** `src/mancala/cli.py`:

```python
"""Terminal interface for hot-seat mancala."""

from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.state import GameState, Player


def _cells(values: list[str]) -> str:
    return ("    " + "  ".join(values)).rstrip()


def render_board(state: GameState, names: dict[Player, str]) -> str:
    """Current player's cups on the bottom row, sowing left to right."""
    bottom = state.current_player
    top = bottom.opponent
    return "\n".join(
        [
            f"{names[top]} (store: {state.stores[top.value]})",
            _cells([f"({i}) " for i in range(6, 0, -1)]),
            _cells([f"[{n:>2}]" for n in reversed(state.board[top.value])]),
            _cells([f"[{n:>2}]" for n in state.board[bottom.value]]),
            _cells([f"({i}) " for i in range(1, 7)]),
            f"{names[bottom]} (store: {state.stores[bottom.value]})",
        ]
    )


def _seeds(n: int) -> str:
    return f"{n} seed" if n == 1 else f"{n} seeds"


def describe_move(
    mover: Player, move: int, events: tuple[Event, ...], names: dict[Player, str]
) -> list[str]:
    sown = sum(isinstance(e, SeedSown | SeedStored) for e in events)
    lines = [f"{names[mover]} sows {_seeds(sown)} from cup {move + 1}."]
    for event in events:
        match event:
            case Captured(by=by, owner=owner, cup=cup, seeds=seeds) if by is not owner:
                lines.append(
                    f"{names[by]} captures {_seeds(seeds)} from {names[owner]}'s cup {cup + 1}."
                )
            case Captured(by=by, cup=cup, seeds=seeds):
                lines.append(f"{names[by]} collects {_seeds(seeds)} from cup {cup + 1}.")
            case ExtraTurn(player=player):
                lines.append(f"{names[player]} gets an extra turn!")
            case GameOver():
                lines.append("The game is over.")
    return lines


def describe_result(state: GameState, winner: Player | None, names: dict[Player, str]) -> str:
    south, north = state.stores
    if winner is None:
        return f"It's a draw, {south}-{north}."
    return f"{names[winner]} wins {max(south, north)}-{min(south, north)}!"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 5 passed

- [ ] **Step 5: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/cli.py tests/test_cli.py
git commit -m "Add CLI board rendering and event narration"
```

---

### Task 13: CLI — game loop and console script

**Files:**
- Modify: `src/mancala/cli.py`
- Test: `tests/test_cli.py` (append)

**Interfaces:**
- Consumes: everything above
- Produces: `main(argv: list[str] | None = None, *, stdin: TextIO | None = None, stdout: TextIO | None = None) -> int` — argparse flags `--variant {kalah,oware}` (default kalah), `--seeds N` (default 4; passed to `initial_state`, so oware rejects non-4 via `parser.error`), positional `names` (0–2; defaults "Player 1"/"Player 2"). Returns 0 on a completed game, 1 on EOF (abandoned). The `mancala` console script (wired in Task 1's pyproject) resolves to this function.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_cli.py`:

```python
import io

from mancala import variants
from mancala.cli import main
from mancala.match import Match


def _run(argv: list[str], user_input: str) -> tuple[int, str]:
    stdout = io.StringIO()
    code = main(argv, stdin=io.StringIO(user_input), stdout=stdout)
    return code, stdout.getvalue()


def test_a_full_game_reports_the_engines_result() -> None:
    # Derive a complete legal game from the engine itself, then replay it
    # through the CLI and check the CLI announces the same outcome.
    match = Match(variants.get("kalah"))
    moves: list[int] = []
    while not match.is_over:
        move = match.rules.legal_moves(match.state)[0]
        match.play(move)
        moves.append(move)
    user_input = "".join(f"{m + 1}\n" for m in moves)

    code, output = _run(["Ana", "Ben"], user_input)

    assert code == 0
    names = {Player.SOUTH: "Ana", Player.NORTH: "Ben"}
    assert describe_result(match.state, match.winner, names) in output


def test_bad_input_reprompts_without_crashing() -> None:
    code, output = _run([], "x\n0\n7\n")
    assert code == 1  # input exhausted -> abandoned
    assert "'x' is not a number between 1 and 6." in output
    assert output.count("choose a cup") >= 4  # initial prompt + one per rejected input
    assert "Game abandoned." in output


def test_illegal_moves_are_reported_and_reprompted() -> None:
    # Kalah: cup 3 from the start lands in the store (extra turn); playing
    # the now-empty cup 3 again is illegal.
    code, output = _run(["--variant", "kalah"], "3\n3\n")
    assert "extra turn" in output
    assert "Cup 3 is not a legal move." in output
    assert code == 1


def test_oware_rejects_nonstandard_seed_counts() -> None:
    import pytest

    with pytest.raises(SystemExit):
        main(["--variant", "oware", "--seeds", "5"], stdin=io.StringIO(""), stdout=io.StringIO())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: new tests FAIL — `ImportError: cannot import name 'main'`

- [ ] **Step 3: Add the game loop to** `src/mancala/cli.py` (add imports `argparse`, `sys`, `from typing import TextIO`, plus `from mancala import variants`, `from mancala.match import Match`, `from mancala.rules import IllegalMoveError`):

```python
def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    parser = argparse.ArgumentParser(prog="mancala", description="Hot-seat mancala.")
    parser.add_argument("--variant", choices=variants.available(), default="kalah")
    parser.add_argument("--seeds", type=int, default=4, help="seeds per cup (kalah: 3-6)")
    parser.add_argument("names", nargs="*", default=[], help="player names (up to two)")
    args = parser.parse_args(argv)
    if len(args.names) > 2:
        parser.error("at most two player names")

    padded = [*args.names, *["Player 1", "Player 2"][len(args.names) :]]
    names = {Player.SOUTH: padded[0], Player.NORTH: padded[1]}
    rules = variants.get(args.variant)
    try:
        match = Match(rules, rules.initial_state(args.seeds))
    except ValueError as error:
        parser.error(str(error))

    def out(text: str = "") -> None:
        stdout.write(text + "\n")

    while not match.is_over:
        out()
        out(render_board(match.state, names))
        mover = match.state.current_player
        stdout.write(f"{names[mover]}, choose a cup (1-6): ")
        stdout.flush()
        line = stdin.readline()
        if not line:
            out()
            out("Game abandoned.")
            return 1
        text = line.strip()
        try:
            cup = int(text)
        except ValueError:
            out(f"{text!r} is not a number between 1 and 6.")
            continue
        if not 1 <= cup <= 6:
            out(f"{cup} is not a number between 1 and 6.")
            continue
        try:
            result = match.play(cup - 1)
        except IllegalMoveError as error:
            out(f"{str(error).capitalize()}.")
            continue
        for message in describe_move(mover, cup - 1, result.events, names):
            out(message)

    out()
    out(render_board(match.state, names))
    out(describe_result(match.state, match.winner, names))
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 9 passed

- [ ] **Step 5: Play a real game by hand** (sanity check the feel — verify the board renders sensibly, moves narrate, and the game ends cleanly):

```bash
uv run mancala --variant kalah Heinrich Nora
```

- [ ] **Step 6: Lint, format, type-check, commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/mancala/cli.py tests/test_cli.py
git commit -m "Add interactive CLI game loop and console script"
```

---

### Task 14: CI

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the complete project
- Produces: CI running lint, format check, type check, and tests on Python 3.13

- [ ] **Step 1: Write** `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"
      - run: uv sync --frozen
      - run: uv run ruff format --check .
      - run: uv run ruff check .
      - run: uv run ty check
      - run: uv run pytest
```

(Bump the action versions to the current majors if newer ones exist.)

- [ ] **Step 2: Verify the workflow steps locally** (CI must never be the first place a command runs):

Run: `uv sync --frozen && uv run ruff format --check . && uv run ruff check . && uv run ty check && uv run pytest`
Expected: all pass. Ensure `uv.lock` is committed — `--frozen` requires it.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml uv.lock
git commit -m "Add CI running ruff, ty, and pytest"
```

- [ ] **Step 4: Push if a remote exists** (if the repo has no GitHub remote yet, leave pushing to Heinrich)

```bash
git remote -v   # if a remote is configured:
git push
```

---

## Final verification

- [ ] `uv run pytest` — everything passes
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run ty check` — clean
- [ ] `uv run mancala --variant oware` — playable
- [ ] `git log --oneline` — one commit per task, working tree clean
- [ ] Invoke superpowers:verification-before-completion before claiming done
