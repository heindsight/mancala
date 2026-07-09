# Mancala Resurrection — Milestone 1 Design

**Date:** 2026-07-09
**Status:** Approved

## Context

This repo holds a mancala game written many years ago in Python 2 + PyGTK 2,
committed for archival ("Add ancient mancala game code to version control").
Neither Python 2 nor PyGTK runs on modern systems. The long-term vision:
a nice UI, network play, computer players, and more game variants.

The project is decomposed into sub-projects, each with its own spec → plan →
implementation cycle. This spec covers only the first: **resurrect the core
game engine, playable hot-seat in the terminal**.

Two ideas from the original design are carried forward in modernized form:

1. **Variants as plugins** — the original's `mgame.games` registry becomes an
   explicit registry over a `Rules` protocol.
2. **Moves as observable step sequences** — the original's generator-based
   `move()` (yield per seed sown, for animation) becomes an immutable event
   list returned with each move result.

The original code itself is not ported: it is Python 2, the engine and UI are
tightly coupled, and mutable state driven by generators cannot support
game-tree search. The ancient files are deleted from the working tree; git
history preserves them.

## Goals

- Clean, tested, UI-agnostic game engine implementing **Kalah** and **Oware**
  with standard rules.
- Simple terminal interface for two-player hot-seat play.
- Foundations the later milestones (AI, web UI, network play) inherit
  without rework: immutable states, pure rules, serializable events.

## Non-goals (later sub-projects)

1. Computer players (minimax/alpha-beta over the immutable states).
2. Web UI (FastAPI + thin JS board; event replay drives animation).
3. Network play (websockets, rooms, server-authoritative state).
4. Additional variants (Congkak, Bao, …).

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.13+ | Strongest language for the maintainer; fully adequate for engine, AI, and server milestones |
| Architecture | Immutable core, pure rules, thin stateful wrapper | Free state exploration for AI; trivial serialization for network; event replay for UI animation |
| State type | `typing.NamedTuple` | True immutability, hashable by default (AI transposition tables), `_replace`, cheap construction. Trade-off accepted: NamedTuples are tuples (equality with plain tuples, unpacking) — harmless at this scale |
| Project management | uv, src layout | Modern standard toolchain |
| Lint/format | ruff | — |
| Type checking | **ty** (strict as practical); fall back to **mypy** if ty's beta rough edges bite | Maintainer preference; small greenfield codebase with plain modern typing is where ty is safest |
| Tests | pytest + hypothesis | Property-based invariants from day one |
| Runtime dependencies | None | stdlib argparse covers the CLI |
| CI | GitHub Actions: ruff check, ruff format --check, ty check, pytest, on 3.13 | — |

## Repo layout

```
pyproject.toml           # uv-managed
src/mancala/
    state.py             # GameState (NamedTuple), Player enum
    events.py            # event types
    rules.py             # Rules protocol, MoveResult, IllegalMoveError
    match.py             # stateful Match wrapper
    variants/
        __init__.py      # registry: get(name), available()
        kalah.py
        oware.py
    cli.py               # terminal interface (console script: `mancala`)
tests/
docs/superpowers/specs/
```

## Core model

- **`GameState`** — `typing.NamedTuple`:
  - `board: tuple[tuple[int, ...], tuple[int, ...]]` — one row of cups per
    player, indexed in sowing order from each player's own perspective.
  - `stores: tuple[int, int]`
  - `current_player: Player`
  - Immutable, hashable, trivially serializable.
- **`Player`** — enum of two members with an `.opponent` property.
- **`Move`** — a plain `int` cup index (0-based, mover's perspective). No move
  class until a variant needs one.
- **`MoveResult`** — `state: GameState` plus `events: tuple[Event, ...]`.
  The returned state is fully resolved: sowing, captures, extra turn or turn
  passed, and the end-of-game sweep if the move ended the game.
- **Events** — the animation/narration vocabulary (replaces the original's
  generator yields): `SeedSown(player, cup)`, `SeedStored(player)`,
  `Captured(by, owner, cup, seeds)` (`by` captures from `owner`'s `cup`),
  `ExtraTurn(player)`,
  `GameOver(winner | None)`. Consumers replay them at any pace; the CLI
  narrates them as text.

## Variant protocol & registry

Variants are stateless rules objects:

```python
class Rules(Protocol):
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
    def winner(self, state: GameState) -> Player | None: ...  # None = draw or ongoing
```

`history` is the set of states already seen this game; variants with
repetition rules (Oware) consult it and resolve repetition inside
`apply_move`, so the returned state is always fully resolved and
`is_over`/`winner` remain pure single-state functions. Variants without
such rules (Kalah) ignore it.

Stateless rules + value states mean one `Rules` instance can serve an
interactive match, a game-tree search, and a server session concurrently.

Registry: an explicit dict in `variants/__init__.py` exposing `get(name)` and
`available()`. No import-time self-registration magic.

`apply_move` assumes a legal move; `Match` is the validating entry point.
`initial_state` raises `ValueError` for configurations the variant does not
support (Kalah accepts 3–6 seeds per cup; Oware accepts only 4).

## Rules (standard, from authoritative sources — not ported from the old code)

### Kalah

- 6 cups per side; seeds per cup configurable 3–6, default 4.
- Counterclockwise sowing; own store included, opponent's store skipped.
- Last seed in own store → extra turn.
- Last seed in own **empty** cup with non-empty opposite cup → capture both
  cups' seeds to own store.
- Game ends when either side's cups are all empty; remaining seeds are swept
  to their owner's store.
- Winner: greater store count; equal is a draw.

### Oware

- 6 cups per side, 4 seeds per cup (standard; not configurable).
- Counterclockwise sowing; **origin cup skipped** when sowing 12+ seeds.
- Capture: last seed leaves an opponent cup at 2 or 3 → capture it and chain
  backward through contiguous opponent cups at 2 or 3.
- **Grand slam rule**: a move whose capture would take *all* the opponent's
  seeds is legal, but the capture is forfeited (common tournament rule).
- **Must-feed**: if the opponent has no seeds, the mover must play a move
  that reaches them if one exists; if none exists, the game ends and the
  mover keeps all remaining seeds.
- Game ends immediately when a store exceeds 24; 24–24 is a draw. On this
  (and every) ending, remaining board seeds are swept to their side's owner.
  This is a deliberate canonicalization: standard play just stops at 25+,
  leaving board seeds uncounted. It never changes the winner, and it keeps
  the engine invariants uniform (terminal = empty board, stores always sum
  to 48).
- **Repetition rule**: endgames with few seeds can cycle forever. When
  `apply_move` produces a `GameState` (which includes whose turn it is) that
  already occurred this game — detected via its `history` argument — the
  game ends immediately: each player captures the seeds remaining on their
  own side, with the sweep emitted as events and the returned state
  terminal. This deterministic first-repetition ending is a **house rule**
  chosen for guaranteed termination — standard Abapa treats endless-cycle
  settlement as an agreement between players. (Kalah needs no such rule:
  every seed only moves toward the stores, so its positions cannot repeat.)
  Note for the AI milestone: game-tree search must thread path history into
  `apply_move` to see repetition endings, and transposition tables keyed by
  `GameState` alone are unsound for Oware (the standard graph-history-
  interaction caveat) — keys must include repetition context, or
  transposition reuse must be restricted for this variant.

## Match wrapper

`Match(rules, state)` is the one stateful class:

- Engine functions assume **resolved** states — ones produced by
  `initial_state` or `apply_move`. A hand-built unresolved state (e.g. a
  Kalah position with an empty row that was never swept) has no legal moves
  yet is not "over"; `Match.__init__` rejects such states with `ValueError`
  rather than deadlocking.
- `play(move) -> MoveResult` — validates against `legal_moves`, raises
  `IllegalMoveError`, advances current state.
- `history` — sequence of `(state, move, events)`; enables undo/replay later.
- `state`, `is_over`, `winner` conveniences delegating to `Rules`.
- Threads the set of previously seen states into `apply_move` (it already
  keeps history), so `Match` contains no variant-specific logic. All games
  played through `Match` — including playout-based tests — terminate.

## CLI

Console script `mancala` (stdlib argparse):

- Flags: variant (default `kalah`), seeds per cup (Kalah only), player names.
- Renders the board as ASCII oriented for the current player; prompts for a
  cup number (1–6); narrates events in words
  ("Heinrich captures 5 seeds from cup 3"); announces the result.
- Hot-seat only; no AI.
- Takes its IO streams as parameters (default stdin/stdout) so tests can
  drive it end-to-end.

## Error handling

- `Match.play` raises `IllegalMoveError` for illegal moves; it is the only
  entry point interactive code uses.
- The CLI catches `IllegalMoveError` and malformed input (non-numeric, out of
  range, empty cup) and re-prompts with the reason.
- No tracebacks reach the user.

## Testing

Input/output-driven throughout; no mocks.

- **Rules tests** (the bulk): given a state, applying move *m* yields exactly
  this state and event sequence. Every named rule gets explicit cases with
  descriptive names (e.g. `test_kalah_last_seed_in_store_grants_extra_turn`):
  extra turn, Kalah capture, empty-opposite no-capture, grand slam,
  must-feed, 12+ origin skip, sweep, draw.
- **Full-game scripts**: scripted move lists from a known start through
  `GameOver`, asserting final state — catches rule-interaction bugs.
- **Property tests (hypothesis)**: random legal playouts as strategies;
  invariants: seed conservation (cups + stores constant), every move in
  `legal_moves` is accepted by `apply_move`, events never reference invalid
  cups, `is_over` states have no legal continuation.
- **CLI tests**: feed a scripted game via injected IO streams; assert board
  rendering and winner announcement.
