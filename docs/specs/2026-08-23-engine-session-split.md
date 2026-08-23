# Engine / session / front-end split

**Status:** Ready for agent
**Design detail:** `docs/plans/2026-08-23-engine-session-split.md`
**Vocabulary:** `CONTEXT.md`

## Problem Statement

The mancala engine cannot carry a second front-end without that front-end
duplicating knowledge the engine already holds.

A developer building a web interface today has to hardcode which variants
exist, what may be configured about each one, what values those settings
accept, and which computer difficulties are available. None of it is
discoverable. Worse, some of it is not even true: every variant accepts the
same seeds-per-cup argument, and Oware rejects every value but four — so the
front-end must also hardcode which arguments each variant will silently
refuse.

The engine and the terminal interface additionally share a package directory,
and the leak runs both ways. Save files record the terminal interface's own
`cpu:hard` string convention, so a web interface cannot read a saved game
without reimplementing a CLI parsing rule. The terminal interface reads a
board-size constant out of the engine's variant package to size its own
prompt. Neither layer can be changed without reasoning about the other.

Two earlier attempts at this work were abandoned because the refactor and the
web interface were built together and each destabilised the other.

## Solution

Split the codebase into three layers — engine, session, and front-end — and
make the engine describe itself.

Each variant declares its own configuration as a typed model rather than
accepting a shared argument list. A registry publishes a descriptor per
variant: its identity, its display name, and a machine-readable schema of
everything that may be chosen about it. A front-end reads that schema to build
its own interface, and never needs to know which variants exist.

Anything a variant's rules fix for every game — Oware's four seeds a cup,
both variants' six cups a side — becomes a constant of that variant rather
than a setting that can be offered and then refused.

A new session layer owns the concepts the engine must not know and the
front-ends must not each reinvent: that a game has two seats, that a seat may
be held by a person or by the computer, which difficulties exist, and how a
game is saved and resumed. Both the terminal interface and the future web
interface sit on it.

The refactor lands complete and alone, before any web code is written.

## User Stories

**Discovering what can be played**

1. As a front-end developer, I want to ask which variants exist, so that I do
   not hardcode a list that goes stale when one is added.
2. As a front-end developer, I want each variant to tell me its display name,
   so that I do not maintain my own translation from identifier to label.
3. As a front-end developer, I want a machine-readable schema of each
   variant's settings, so that I can generate a configuration form without
   knowing what the settings are.
4. As a front-end developer, I want each setting's permitted values in that
   schema, so that I can reject bad input before sending it.
5. As a front-end developer, I want each setting's default in that schema, so
   that I can pre-fill a form correctly.
6. As a front-end developer, I want each setting to carry a human-readable
   label and description, so that my form is comprehensible without me writing
   the copy.
7. As a front-end developer, I want a variant with nothing to configure to say
   so explicitly, so that I render no controls rather than special-casing it.
8. As a front-end developer, I want to ask which computer difficulties exist,
   so that I do not hardcode them.
9. As a front-end developer, I want difficulties to carry display names, so
   that the terminal and web interfaces label them identically.
10. As a front-end developer, I want the schema to stay flat, so that I can
    read it without resolving cross-references.
11. As a maintainer, I want the published schema pinned by a test, so that a
    dependency upgrade that changes it fails the build rather than a browser.

**Starting and configuring a game**

12. As a player, I want to choose a variant when starting a game, so that I can
    play the one I want.
13. As a player, I want to set a variant's options when starting a game, so
    that I can play a longer or shorter game.
14. As a player, I want to be shown only the options that apply to the variant
    I chose, so that I am not offered a setting that will be refused.
15. As a player, I want an out-of-range setting rejected with a clear message,
    so that I can correct it.
16. As a player, I want a setting belonging to a different variant rejected
    rather than ignored, so that I never get a game I did not ask for.
17. As a terminal user, I want per-variant help text, so that I can discover a
    variant's options without reading the source.
18. As a terminal user, I want a variant's options to have sensible defaults,
    so that I can start a game without specifying anything.

**Seating players**

19. As a player, I want to name each seat, so that the board and the commentary
    address me by name.
20. As a player, I want to hand either seat to the computer, so that I can play
    against it from whichever side I prefer.
21. As a player, I want to hand both seats to the computer, so that I can watch
    a game play out.
22. As a player, I want to choose the computer's difficulty per seat, so that
    two computers can play at different strengths.
23. As a front-end developer, I want a structured seat rather than a string
    convention, so that I do not reimplement another interface's parsing rule.
24. As a front-end developer, I want seats keyed by which side of the board they
    hold, so that I cannot silently swap them by mis-indexing.

**Playing**

25. As a player, I want the board rendered with my cups nearest me, so that I
    can read the position at a glance.
26. As a player, I want to be told what each move did — seeds sown, captures,
    extra turns — so that I can follow the game.
27. As a player, I want an illegal move refused with a reason, so that I can
    pick again.
28. As a player, I want the computer's move announced as it is made, so that a
    computer-versus-computer game is watchable rather than silent until the end.
29. As a front-end developer, I want to advance a computer's turn one move at a
    time, so that I can render or animate between moves.
30. As a front-end developer, I want to ask whose turn it is and whether that
    seat is a person, so that I know whether to prompt or to advance.
31. As a front-end developer, I want advancing a computer's turn to be refused
    when a person is on turn, so that a bug in my code surfaces immediately
    rather than playing a move on the person's behalf.
32. As a player, I want the game to end and declare a result, so that I know who
    won and by how much.
33. As a player, I want a repeated position to end an Oware game, so that a
    cycle cannot continue forever.

**Saving and resuming**

34. As a player, I want to save a game in progress, so that I can stop and
    continue later.
35. As a player, I want a resumed game to have the same players in the same
    seats, so that I continue the game I saved.
36. As a player, I want a resumed game to have the same variant and settings, so
    that the rules do not change under me.
37. As a player, I want a resumed game to remember every position already
    reached, so that Oware's repetition rule still applies.
38. As a player, I want a corrupt or hand-edited save rejected with a clear
    reason, so that I do not resume into a nonsensical position.
39. As a player, I want a save whose recorded position disagrees with its own
    move history rejected, so that a change in the rules cannot silently hand me
    a different game.
40. As a front-end developer, I want a saved game readable without knowing any
    interface's input conventions, so that a game saved in one interface can be
    resumed in another.
41. As a maintainer, I want the saved settings recorded as a structured object,
    so that adding a variant setting later needs no change to the save code.

**Maintaining**

42. As a maintainer, I want to add a variant by writing one module, so that both
    front-ends offer it without being touched.
43. As a maintainer, I want a variant's settings validated where they enter the
    system, so that the rules code can trust what it is handed.
44. As a maintainer, I want a mismatched variant-and-settings pairing to be
    impossible to express, so that the type checker catches it rather than a
    user.
45. As a maintainer, I want the engine to have no knowledge of participants, so
    that I can change how games are seated without touching the rules.
46. As a maintainer, I want the computer's move selection unable to see who
    holds each seat, so that it cannot accidentally play differently against
    different opponents.
47. As a maintainer, I want board size read from the position rather than a
    shared constant, so that a future variant with a different board needs no
    change to shared code.
48. As a reviewer, I want the file moves reviewed separately from the behaviour
    changes, so that I can verify the move changed nothing.
49. As a maintainer, I want the decisions behind this structure recorded, so
    that a future reader does not have to reconstruct them.

## Implementation Decisions

**Layering.** Three layers in one distribution: engine, session, front-end. The
boundary is enforced by the import graph at review, not by separate packages.
The engine knows positions, legal moves, and how a move resolves. The session
layer knows seats, computer players, and persistence. Front-ends own all input,
output, and presentation.

**Variant descriptors.** A registry maps a variant identifier to a descriptor
carrying identity, display name, config model, and a factory. `Rules` becomes a
configured instance rather than a stateless singleton, and gives up its `name`
— identity belongs to the descriptor.

**Descriptors parse their own options.** The descriptor exposes a creation
method taking a plain mapping, not a config object. This came out of a
prototype: it is the only shape in which a mismatched pairing is *not
expressible* rather than merely discouraged, and it matches the front-end path
exactly (arguments or JSON → identifier → mapping → create).

```python
def create(self, options: Mapping[str, Any] | None = None) -> Rules:
    return self.factory(self.config_model.model_validate(options or {}))
```

Generic descriptors were prototyped and rejected: both real lookups pass a
runtime string, so a type parameter is erased exactly where it would matter,
and the registry cannot hold the bound at all under invariance.

**Config models.** Per-variant pydantic models, frozen, with `extra="forbid"` —
without which a setting belonging to another variant is silently accepted and a
default game handed back. Ordinal settings are bounded; categorical settings use
inline literals rather than enum types, which keeps the emitted schema flat and
free of cross-references. A variant with nothing to configure has an empty
model rather than no model, so no caller branches on absence.

**Discovery.** The published contract is the config model's generated JSON
Schema. Display names and field labels live with the models, in English, so
that adding a variant is a one-file change both front-ends pick up. There is no
unified catalogue call: variants belong to the engine and difficulties to the
session layer, and a web handler composes its own response.

**Validation.** pydantic parses at boundaries only. Positions and events stay
plain immutable types — positions are hashed on every node of the computer
player's search. Any protocol member typed as a base class is exposed as a
read-only property, never a bare attribute; a prototype confirmed that a mutable
protocol attribute is invariant and cannot be satisfied.

**Session.** Constructed from a descriptor, an options mapping, and seats keyed
by side. Holds a private match and delegates position, legality, result and
history. Adds whose turn it is, and a method that plays exactly one computer
move — refusing when a person is on turn, since its caller is a separate
program. It plays one move rather than running to the next human turn so that
nothing does unbounded work in a single call and both front-ends can render
between moves.

**Seats.** A discriminated union of a person with a name and a computer with a
difficulty, as frozen models. The name is an opaque label the session layer
never interprets. Difficulty is a closed named set, not a parameter.

**Computer players.** Move selection is handed a match, never a session, so it
cannot read the seats.

**Persistence.** A new document version, rejected rather than migrated — the
previous version ships in no release and exists only in tests. It records the
variant identifier, the validated settings as an object, structured seats, the
move history, and the resulting position. Seats are stored under explicit
side-named fields: serialising a side-keyed mapping directly renders the keys as
the underlying integers, and the side enum cannot become a string enum because
those integers index the board throughout the engine. Loading replays the
history and rejects a document whose recorded position disagrees with the
replay.

**Terminal interface.** Variant becomes a subcommand, with each variant's
options built from the published schema rather than from the models directly —
so the discovery contract has a real consumer before the web interface exists.
The `cpu:` prefix stays here: it is an argument-encoding convention, not a
domain concept.

**Sequencing.** Six steps, each independently landable and green: retire the
superseded design document; move files with no behaviour change; remove the
shared board-size constant; introduce descriptors and config models; introduce
the session layer; new save format.

## Testing Decisions

**What makes a good test here.** Tests assert externally observable behaviour:
what a player sees, what a front-end can discover, what a saved file contains
and refuses. They do not assert that a particular function was called or that a
value took a particular internal route. Test names describe the behaviour; test
bodies use bare assertions and contain no flow control.

**The refactor is proven by tests that already exist.** Most of this work
changes no observable behaviour, and the existing suites — full-game playthroughs,
property-based invariants, and the terminal interface's own tests — are what
demonstrate that. New tests written against new internals would only demonstrate
that the internals exist. Steps that move files or relocate constants should add
close to nothing.

**Seam 1 — the terminal interface entry point (existing).** The highest seam
available and already the largest suite in the project. Everything user-facing
is asserted here: starting a game with a variant and options, rejection of bad
and foreign options, per-variant help, seating people and computers, playing,
illegal moves, game end, saving, resuming, and refusal of corrupt saves.

**Seam 2 — the variant registry and its published schema (existing, extended).**
The registry's existing tests grow to cover descriptors and to snapshot each
variant's emitted schema. This seam exists because the schema is a contract for
a consumer that does not exist yet: the entry-point seam can only show that
argument parsing happened to work, not pin what a browser will read.

**Seam 3 — the session layer.** Justified by one contract the entry point cannot
reach: advancing a computer's turn must be refused when a person is on turn.
Its caller is a separate program, so this guards a public entry point against
its caller rather than against an unreachable internal state — unlike the match
constructor's unresolved-position guard, which is removed in this work precisely
because nothing can reach it.

**Existing seams move rather than multiply.** Persistence and computer-player
tests follow their modules into the session layer. Variant rule tests stay where
they are and construct variants with their config models. Position and event
type tests are unaffected.

**Prior art.** The terminal interface's existing tests drive the entry point with
argument lists and string streams — that pattern carries forward unchanged. The
property-based suite and the full-game playthroughs are the existing model for
asserting engine invariants without reaching inside.

**Coverage.** The hundred-percent gate stays. Any lower threshold is arbitrary
and only relocates the argument to which lines do not count.

## Out of Scope

- **Any web interface code.** That is the next piece of work. This refactor
  lands complete and alone; conflating them is what ended two earlier attempts.
- **Rule toggles** for either variant. The configuration machinery is built to
  carry them; neither variant gains a second ruleset here.
- **Board size as a setting.** It is a constant of each variant today.
- **A command-line framework.** Investigated and rejected for this work: the
  obvious candidate cannot build parameters from runtime data, and its only
  escape hatch discards the help text and validation that are the point of
  publishing a schema. If the terminal interface is ever reframed it should be
  on that library's underlying layer, as separate work.
- **Network play and further variants.** Recorded on the roadmap.
- **Migrating existing save files.**

## Further Notes

Three decisions are recorded as ADRs alongside the work: taking a validation
library as the project's first runtime dependency, which supersedes an earlier
decision to have none; publishing generated JSON Schema as the discovery
contract rather than a curated parameter description; and configured rules
instances with descriptors replacing stateless singletons. A fourth ADR
preserves the still-live decisions from the superseded design document before it
is deleted. The layering itself gets no ADR — it is conventional, and the
glossary carries the vocabulary.

## Weak Points

Written last, honestly.

**The user stories are inferred, not gathered.** There is one user of this
project and he did not write them. They are my reconstruction of what the design
interview implied, and story 31 in particular exists because a guard was
retained, rather than the guard existing because someone wanted the behaviour.

**Seam 3 is justified by exactly one assertion.** A whole test module for the
refusal case is a poor ratio, and the coverage gate is part of why it exists. I
argued against this seam, was corrected on good grounds, and have not
re-examined whether other session behaviour deserves testing there — so it is
either under-specified or the seam is over-built, and I do not know which.

**"The refactor is proven by existing tests" is an assertion I have not
measured.** The existing suites are strong, but I have not checked whether the
terminal interface tests actually exercise every path the restructure touches,
and the coverage gate will discover any gap at the least convenient moment.

**The terminal interface's option-building is still unwritten.** Every claim
about reading the published schema directly rests on a schema I have generated
but a reader I have not.

**Two decisions in this spec revise ones already approved**: the session
constructor takes an options mapping rather than a settings object, and the
descriptor parses rather than receiving a parsed object. Both followed from a
prototype, both are argued in the design document, and both are mine rather than
the maintainer's.

**Testing conclusions rest on one type checker.** The project keeps a documented
fallback that has not been run against any of this.
