# pydantic as a runtime dependency

This supersedes the "No runtime dependencies" decision in ADR 0000.

Each variant now declares what may be configured about it as a pydantic model.
pydantic parses a variant's options where they enter the system, and it
generates the JSON Schema that front-ends read (ADR 0003). It is the project's
first runtime dependency.

pydantic parses input at boundaries only. Inside the engine, the only pydantic
types are the config models. Each rules object holds one, already parsed.
Positions and events stay plain `NamedTuple`s. A computer player hashes a
position at every node of its search, so positions must stay cheap to build and
compare.

## Considered options

**Keep writing validators by hand.** Every variant would need its own range
checks, its own refusal of unknown settings, and its own schema description,
kept in step with each other by hand. The schema is a contract with a front-end
that does not exist yet, so a hand-written one would drift without anything to
notice.

**dataclasses with a separate schema library.** This splits one declaration
into two that must agree. pydantic builds the validator and the schema from the
same annotations.

## Consequences

A config model must set `extra="forbid"`. By default pydantic ignores a setting
it does not declare. Kalah's `seeds_per_cup` handed to Oware would then be
dropped silently, and the caller would get a default Oware game.

A pydantic upgrade can change the emitted schema. Each variant's schema is
pinned by a test, so such a change fails the build.
