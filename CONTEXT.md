# Context

Domain vocabulary for the mancala project. Glossary only — no implementation
detail, no design decisions. Decisions live in `docs/adr/`.

## Layers

**Engine** — the rules of mancala. Knows positions, legal moves, and how a move
resolves. Does not know that a game has participants, that a participant might
be a person, or that a game might be saved.

**Session** — one game being played by two parties. Knows who holds each side,
that a side may be held by a computer, and how to persist and resume the game.

**Front-end** — a program a person uses to play: the terminal interface, and
(next) the web interface. Owns all input, output, and presentation.

## Playing terms

**Cup** — one of the six hollows on a side of the board that holds seeds.
Numbered from 1 at the prompt, indexed from 0 in code, always counted in the
direction the holder sows.

**Store** — the pit that accumulates a side's captured seeds. Not a cup: seeds
in a store are never sown again.

**Sow** — to lift the seeds from one cup and drop them one at a time into
successive cups, in the direction of play.

**Capture** — to take seeds off the board into a store. Which seeds, and under
what condition, is the variant's business.

**Move** — a choice of which of the holder's own cups to sow. Identified by
its cup index from the holder's own perspective, so cup 0 means a different
physical cup depending on who is moving.

**Position** — the complete state of a game at one instant: the seeds in every
cup, the seeds in both stores, and whose turn it is. Carries no history.

**Event** — one thing that happened while a move resolved: a seed sown, a seed
stored, a capture, an extra turn, the game ending. A move produces an ordered
sequence of them, which is how a front-end can animate or narrate what the
engine did without re-deriving it.

## Structural terms

**Player** — a *side* of the board, south or north. Not a participant. South
always moves first.

**Seat** — a *participant*: whichever party holds one side of a match. A seat is
held by a person or by the computer. `Player` says which end of the board;
`Seat` says who is at it. Keep them distinct.

**Variant** — a named member of the mancala family: Kalah, Oware. Two variants
differ in how a move resolves, not in how the board is described.

**Rules** — the mechanics of one variant, configured for one game. Pure: given a
position and a move, produces the next position and its events. Holds nothing
about the game in progress.

**Variant config** — the parameter values chosen for one particular game of one
variant, such as Kalah's seeds per cup. Anything a variant's rules fix for
every game of that variant is a constant of the variant, not a config
parameter: Kalah has six cups a side and Oware starts with four seeds a cup
because those are what the games *are*.

**Variant descriptor** — a variant's identity and its configuration surface:
what it is called, and what may be chosen about it. What a front-end reads to
offer a choice of games, without knowing which variants exist.

**Match** — one game's progression: its current position, the moves played to
reach it, and every position it has passed through. The last of those is not
bookkeeping — Oware ends a game that repeats a position, so a match without its
seen positions is a match that need not terminate.

**Session** — a match together with its seats.

**Difficulty** — a named computer-player skill level. A closed set: a
difficulty is a name, not a knob.
