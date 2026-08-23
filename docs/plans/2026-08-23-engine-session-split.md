# Engine / session / front-end split

**Date:** 2026-08-23
**Status:** Proposed — revised after review

## Goal

Make the codebase able to carry a second front-end. Three defects block that
today:

1. **`Rules.initial_state(seeds_per_cup)` is dishonest.** Every variant takes
   the same keyword argument and Oware rejects every value but 4.
2. **Nothing is discoverable.** A front-end cannot ask which variants exist,
   what may be configured about each, or which difficulties are available. It
   must hardcode all three.
3. **Engine and CLI are tangled.** They share a package directory;
   `save.py` serialises the CLI's `"cpu:hard"` string convention, and
   `cli.py` imports `variants.CUPS` to size its own prompt.

Plus one smaller one: save-file loading and parameter checking are hand-rolled
validators.

**The web UI is not part of this work.** Previous attempts were abandoned
because refactor and UI got conflated. This lands first, alone.

## Target layout

```
src/mancala/
    engine/            # the rules of mancala; knows nothing of participants
        state.py       # GameState, Player
        events.py
        rules.py       # Rules protocol, Move, MoveResult, IllegalMoveError
        match.py       # Match
        variants/
            __init__.py    # registry: all(), get(id)
            descriptor.py  # VariantDescriptor
            _common.py
            kalah.py       # Kalah + KalahConfig
            oware.py       # Oware + OwareConfig
    session/           # one game, played by two parties
        session.py     # Session
        seats.py       # Seat = Human | Computer
        strategies.py  # Difficulty, Strategy protocol + implementations
        persistence.py
    cli/               # all terminal I/O and presentation
        main.py
        play.py
        render.py
tests/
    engine/  session/  cli/
```

One distribution. No separate packages: the boundary is enforced by the import
graph at review, not by dependency resolution.

Vocabulary for all of this is in `CONTEXT.md`.

---

## Step 0 — Retire the old spec (docs only, no code)

- Write `docs/adr/0000-founding-decisions.md`, capturing the still-live rows of
  the milestone-1 decision table **with their rationale**: Python 3.13+;
  immutable core / pure rules / thin stateful wrapper; `NamedTuple` state and
  its accepted trade-off; uv + src layout; ruff; ty with mypy as fallback;
  pytest + hypothesis; **zero runtime dependencies**; GitHub Actions CI.
- Write `docs/roadmap.md` from the spec's "Non-goals (later sub-projects)"
  list, updated: computer players are done; web UI, network play, and further
  variants remain.
- Delete `docs/superpowers/specs/2026-07-09-mancala-resurrection-design.md`
  and `docs/superpowers/plans/2026-07-09-mancala-engine-cli.md`.

ADR 0 exists so that ADR 1 can **supersede** its zero-dependency decision,
rather than citing a file that no longer exists.

## Step 1 — Move files (no behaviour change)

Pure motion into the layout above. Only imports change. `cli.py` splits into
`main.py` / `play.py` / `render.py` by moving functions, unchanged. Tests move
to mirror the packages. `_common.CUPS` still exists and is still re-exported
for the CLI.

Reviewed *as* pure motion: no semantic change belongs in this step.

## Step 2 — Remove the shared `CUPS`

`CUPS = 6` is shared state pretending to be a rule. Cups per row is a constant
of each variant, not a parameter of it (Kalah and Oware both happen to use 6;
a future variant need not).

- Each variant module carries its own cup count; `_common.CUPS` is deleted and
  no longer re-exported.
- `_common` helpers read board shape from the state they are handed.
- Oware's `_TARGET = 24` is derived from the starting seed total, not written
  as a literal.
- The CLI's prompt range comes from `len(state.board[mover.value])` — the
  state it is already rendering. No geometry API is added; the board's shape
  is readable off any position.

## Step 3 — Variant descriptors and config models

The core of the refactor. pydantic becomes a runtime dependency.

- `VariantDescriptor`: `id`, `display_name`, `config_model`, and a factory —
  with **`create(options: Mapping[str, Any] | None) -> Rules`** doing the
  parsing: `factory(config_model.model_validate(options or {}))`.
  The descriptor takes a mapping, not a config object, so
  `get("oware").create(KalahConfig())` is not expressible rather than merely
  discouraged. This mirrors the front-end path exactly
  (argv/JSON → id → dict → `create`) and puts the single parse at the boundary.
  `config_model` stays public for `model_json_schema()`.
- **`Rules` exposes `config` as a read-only `@property`, never a bare
  attribute.** Verified: a protocol attribute is invariant, so
  `config: BaseModel` requires implementers to accept writes of *any*
  `BaseModel` and no variant satisfies the protocol. Same applies to any future
  protocol member whose type is a base class.
- Config models set **`extra="forbid"`**. Verified: pydantic's default silently
  accepts `oware.create({"seeds_per_cup": 4})` and hands back a default Oware —
  exactly the class of bug this refactor exists to remove. It adds
  `"additionalProperties": false` to the schema, which stays flat.
- `KalahConfig` — `seeds_per_cup: Annotated[int, Field(ge=3, le=6, title=...,
  description=...)] = 4`. A **range**, not an enum: "Kalah is played with 3 to
  6 seeds a cup" is an ordinal statement, and it widens cleanly.
- `OwareConfig` — **no fields**. Oware has nothing to choose. Every variant has
  a config model, so no caller ever branches on `None`, and it serialises to
  `{}`, which is what old saves should mean once Oware gains its toggles.
- Config models are `frozen=True`, which also makes them hashable.
- **Categorical config fields use `Literal`, never `StrEnum`.** Verified: a
  `Literal` inlines as `"enum": [...]` in the property, while a `StrEnum`-typed
  field emits `$ref` into `$defs`. Keeping every field inline is what keeps the
  schema flat and the CLI's schema reader free of `$ref` resolution. So Oware's
  eventual grand-slam toggle is `Literal["legal", "forfeits", "illegal"]`.
  (`Difficulty` stays a `StrEnum` — it is a seat's attribute, not a config field.)
- `Rules.initial_state()` takes no arguments. Each variant is constructed with
  its config and carries it.
- `Rules.name` is removed — identity belongs to the descriptor. `Match` never
  needs to know what game it is; the descriptor is threaded to `persistence`
  alongside the match until step 4 gives it a `Session` to read it from.
- `Rules` stays a non-generic `Protocol`, and so does `VariantDescriptor`.
  Prototyped and rejected: a `VariantDescriptor[ConfigT]` catches a mismatched
  pairing only on a *direct* descriptor reference, and no caller has one —
  both real lookups pass a runtime `str` (`cli.py:106`, `save.py:87`). The
  registry cannot even hold the bound: `dict[str, VariantDescriptor[BaseModel]]`
  is rejected by invariance, so `Any` is forced rather than chosen. Parsing
  inside `create` closes the hole that generics could not.
- Registry: `variants.all()` and `variants.get(id)` return descriptors.
- **Discovery is `config_model.model_json_schema()`**, snapshot-tested per
  variant so a pydantic upgrade that changes the output fails CI rather than
  the browser. Labels (`display_name`, field `title`/`description`) live here,
  in English, so adding a variant is a one-file change both front-ends pick up.
- **No unified catalogue call.** Variants are an engine concept, difficulties a
  session one; a web handler composes its own response.
- CLI becomes `mancala new <variant> [--options]`, with each variant's
  subparser built **from the emitted JSON Schema**. Not from `model_fields`:
  since the web UI is deferred, reading the schema is the only way the
  discovery contract gets a real consumer before a browser app is sitting on it.
- ADRs 1, 2 and 3 are written in this step.

## Step 4 — The session layer

- `seats.py` — `Human(name: str)` and `Computer(difficulty: Difficulty)` as
  **frozen** pydantic models carrying `kind` discriminators;
  `type Seat = Annotated[Human | Computer, Field(discriminator="kind")]`.
  `name` is an opaque label the session layer never interprets.
- `strategies.py` — moves here from the engine, and carries `Difficulty`
  (a `StrEnum`) plus the `Difficulty → Strategy` mapping. No separate
  `difficulty.py`: the enum and the mapping it keys are one concern, and
  `strategies` imports nothing from `seats`, so there is no cycle to break.
  `Strategy.choose()` keeps taking a **`Match`**: a strategy handed a `Session`
  could read the seats, and a computer player that can see who it is playing is
  a bug waiting to happen.
- `session.py` — `Session(variant, options, seats: Mapping[Player, Seat])`.
  ⚠️ **Revised:** `options` is the same mapping `create` takes, not a
  pre-built config object — the alternative reopens at `Session`'s door the
  exact mismatch step 3 closes at the descriptor's. `Session.config` reads
  through to `rules.config`.
  Holds a **private** `Match`; delegates `state`, `is_over`, `winner`,
  `legal_moves`, `history`; adds `on_turn -> Seat`, `variant`, `config`,
  `seats`, `play(move)`, and `play_computer_move()`.
- `play_computer_move()` plays **one** move and raises if a human is on turn.
  The front-end loops on `on_turn`. Nothing does unbounded work in one call,
  and both front-ends keep per-move rendering.
- **`Match`'s "unresolved state" guard is deleted**, with its test. It rejects a
  state that has no legal moves but is not over — reachable only by handing
  `Match` a state that came from neither `initial_state` nor `apply_move`. Once
  `Session` is the construction path, nothing in the codebase can do that. It
  is defensive programming for a contrived case; if a real one turns up, it
  comes back with the case that justified it.
- The `cpu:<difficulty>` prefix stays in the CLI: it is an argv encoding, and a
  web UI would send a structured seat. The CLI parses it into a `Computer`.
  `ComputerPlayer`'s move-announcement stays in the CLI as rendering.
- Seats are keyed by `Player`, not indexed by `Player.value`. Positional
  indexing is how sides get silently swapped, and it is why the CLI currently
  maintains a parallel `names` dict.

## Step 5 — Save format v2

- A pydantic `SaveDocument`: `format`, `version: 2`, metadata (variant id,
  **config object verbatim**, seats, `saved_at`), history, state.
- The stored config is `rules.config.model_dump()` — the *validated* config,
  not the raw options mapping, so defaults are recorded explicitly and a save
  says what it was played with rather than what was typed.
- Storing the config as an object means future parameters and rule toggles
  need no change to `persistence.py`.
- Seats serialise through their `kind` discriminators.
- **Seats are keyed by explicit `south` / `north` fields in the document, not by
  serialising a `Mapping[Player, Seat]`.** Verified: pydantic renders `Player`
  keys as `"0"` / `"1"` — the enum values — which is both unreadable and
  hostile to ever renumbering the enum. `Player` cannot become a `StrEnum` to
  fix this, because `state.board[player.value]` indexes on those integers
  throughout the engine.
- v1 is **rejected, not migrated**. It is one month old, ships in no release,
  and exists only in `tests/test_save.py`. A migration path for a format with
  no files in the wild is code that never runs in anger.
- **The replay cross-check stays.** It earns its place precisely because of
  this refactor: it turns "the engine now replays this differently" into a loud
  load error instead of a silently different game. The accepted consequence is
  that a genuine rules bugfix invalidates existing saves — which is correct.

---

## Decisions recorded as ADRs

| # | Decision | Step |
|---|---|---|
| 0 | Founding decisions (extracted from the deleted spec) | 0 |
| 1 | pydantic as a runtime dependency — **supersedes ADR 0's zero-dependency decision** | 3 |
| 2 | JSON Schema as the parameter-discovery contract, over curated parameter specs | 3 |
| 3 | Configured `Rules` instances and variant descriptors that parse their own options, replacing stateless singletons | 3 |

Engine/session/front-end layering gets no ADR: it is conventional, a reader
will not ask why, and `CONTEXT.md` already carries the vocabulary.

## Deliberately not in scope

- **Any web code.** That is the next piece of work, not this one.
- **Rule toggles** (Kalah capture-on-empty, Oware grand-slam). The config
  machinery is built to carry them; neither variant gets a second ruleset here.
- **Cups per row as a parameter.** It is a constant of each variant today.
- **A CLI framework.** Typer cannot build parameters from runtime data — its
  model is that the function signature *is* the CLI, and its only escape hatch
  (`allow_extra_args`) discards help, validation and completion, which is the
  whole point of the schema. If the CLI is ever reframed, it should be on
  **Click**, which supports runtime-constructed commands, and it should be its
  own piece of work after step 5.

---

## Weak points

Written last, from actually writing the above. Revised after review.

**I proposed swapping steps 3 and 4, confidently, and it was wrong.** Both
halves of my reasoning were overstated: threading a descriptor into `dump()` is
an intermediate signature, not throwaway scaffolding, and "the CLI gets rewired
twice" was two different files. The real dependency runs descriptors → session,
because `Session(variant, config, seats)` is *made of* descriptor types — which
is what made the swapped order circular. Caught in review, not by me.

**My `StrEnum` rule of thumb for config toggles was wrong, and I stated it as a
rule.** A `StrEnum`-typed field emits `$ref` into `$defs`; a `Literal` inlines.
Since the flat schema is the whole argument for the CLI reading it directly, I
had it backwards. Found by running it, after asserting it.

**The `Player`-keyed seats mapping was specified without checking how it
serialises.** It renders keys as `"0"` / `"1"`. The fix is small and it is in
the plan, but the pattern concerns me more than the instance: I specified a
type and a document format in the same breath without checking they agreed.

**The step-3 descriptor in the previous draft did not type-check.** I wrote
`create: Callable[[BaseModel], Rules]` and never ran it. It fails
contravariance — a callable declared to take any `BaseModel` cannot be
satisfied by `Kalah.__init__`, which takes only `KalahConfig` — and would have
forced an explicit `Any` at every registration site. Found by prototype, and
confirmed independently. It is now fixed, but the plan asserted a type
signature I had not compiled.

**I recommended against generic `Rules` on incomplete grounds and got the right
answer anyway.** My reason (the type parameter infects `Match`, the strategies
and `_Node`) was true but was not the load-bearing one. The real reason is that
both lookups pass a runtime `str`, so genericity is erased exactly where it
would matter. I did not know that when I recommended it, and the resolution —
moving the parse into `create` — came from the prototype, not from me.

**The schema-driven argparse builder is still unwritten.** It is better
evidenced than it was — I have the actual emitted schema, now seven flat keys
with `additionalProperties`, and the `Literal` rule keeps `$ref` out of it
permanently. But "~20 lines" remains an estimate I have not paid for. It is now
the largest unmeasured claim left in this document.

**`Session(variant, options, seats)` revises a shape you approved.** You chose a
constructor taking a config object. Keeping it would reopen at `Session` the
mismatch step 3 closes at the descriptor, so I changed it — but it is a
decision of yours that I have altered on my own reasoning, not a detail.

**Untested consequence of the same change.** Nothing can now hand a descriptor a
pre-built typed config. Tests and programmatic callers go direct
(`Kalah(KalahConfig(...))`) and are unaffected, but a build-adjust-recreate flow
would have to round-trip through `model_dump()`. I do not believe anything needs
that; I have not looked for it.

**Prototyped against `ty` only.** mypy was not run, and the project keeps mypy
as a documented fallback. If ty's beta rough edges ever force that switch, none
of the typing conclusions above have been checked against it.

**Rework I chose rather than avoided.** `persistence.py` is edited in step 3
(threading the descriptor) and rewritten in step 5. That is the price of
keeping steps reviewable in isolation, and I think it is worth paying, but it
is duplicated effort and not an accident of ordering.

**A line drawn in two directions.** Discovery is deliberately *not* unified —
variants and difficulties stay in their own layers and the web UI composes its
own catalogue response — while display strings deliberately *are* unified in
the backend so front-ends do not duplicate them. Both are defensible; they are
not the same instinct, and I applied them to the same API surface.
