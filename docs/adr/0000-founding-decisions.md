# Founding decisions

These decisions were made on 2026-07-09, when the project was restarted from
an old Python 2 and PyGTK 2 game. Neither of those runs on a modern system.
The first milestone was a tested game engine for Kalah and Oware, playable
hot-seat in the terminal. Later milestones were to add computer players, a web
interface, network play and more variants. So these decisions were made to
serve those later milestones as well as the first one.

The old code was not ported. It was Python 2, its engine and interface were
tightly coupled, and its state was mutable and driven by generators. Mutable
state of that kind cannot support a game-tree search. Git history keeps the
old files.

## Python 3.13 or later

Python is the maintainer's strongest language. It is fully adequate for the
engine, the computer players and a server.

## Immutable core, pure rules, thin stateful wrapper

- A position is an immutable value.
- A variant's rules are pure functions. Given a position and a move, they
  return the next position and the events the move produced. The returned
  position is fully resolved: sowing, captures, the extra turn or the change of
  turn, and the end-of-game sweep if the move ended the game.
- One small stateful class, `Match`, holds the game in progress. It is the only
  place that checks a move is legal, and it keeps the history of the game.

The reasons:

- **Computer players.** A search can explore positions freely, because nothing
  it looks at can change under it.
- **Network play.** A value is trivial to serialise.
- **Animation.** A front-end replays the events at its own pace to animate or
  narrate a move. It does not need to work out again what the engine did. This
  replaces the old code's generator, which yielded once per seed sown.

Because rules hold no state, one rules object can serve an interactive match, a
game-tree search and a server session at the same time.

Oware ends a game that repeats a position, so its rules need to know which
positions the game has already reached. The rules take those positions as an
argument instead of storing them. Deciding whether a position is over, and who
won it, then still needs only that position.

## Positions are `NamedTuple`s

A `typing.NamedTuple` is truly immutable. It is hashable by default, which a
computer player needs for transposition tables. It has `_replace`, and it is
cheap to construct.

The trade-off is that a `NamedTuple` is a tuple. It compares equal to a plain
tuple with the same values, and it can be unpacked. This was accepted, because
it does no harm in a codebase this size.

## Toolchain

| Tool | Choice | Reason |
| --- | --- | --- |
| Project management | uv, with a `src` layout | The modern standard toolchain. |
| Lint and format | ruff | No reason was recorded. |
| Type checking | ty, as strict as practical | The maintainer's preference. A small new codebase with plain modern typing is where ty is safest. |

ty is in beta. If its rough edges cause problems, the fallback is mypy.

## Testing with pytest and hypothesis

Tests use pytest. They also use hypothesis, so that property-based invariants
are tested from the start.

- **Rules tests** are most of the suite. Each one starts from a given position,
  plays one move, and asserts the exact position and events that result. Every
  named rule has its own cases with descriptive names.
- **Full-game scripts** play a scripted list of moves from the start to the end
  of a game and assert the final position. They catch bugs in how rules
  interact.
- **Property tests** play random legal games and check invariants. Seeds are
  conserved. Every legal move is accepted. Events never refer to a cup that
  does not exist. A finished game has no legal move.

## No runtime dependencies

The project has no runtime dependencies. The standard library's `argparse` is
enough for the terminal interface.

## Continuous integration

GitHub Actions runs the ruff lint and format checks, ty and pytest. No reason
was recorded.
