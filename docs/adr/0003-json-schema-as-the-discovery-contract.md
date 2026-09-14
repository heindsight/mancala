# Generated JSON Schema as the discovery contract

A front-end finds out what may be configured about a variant by reading the
JSON Schema of the variant's config model. The schema is generated from the
model. It carries each setting's type, permitted values, default, label and
description. A variant with nothing to configure publishes a schema with no
properties, so a front-end renders no controls and needs no special case.

Labels and descriptions are written in English, in the config model, next to
the setting they describe. Adding a variant is then one module, and every
front-end picks it up.

## The schema stays flat

A front-end must be able to read the schema without resolving
cross-references. So a categorical setting is typed as an inline `Literal`,
never as an enum class. pydantic writes a `Literal` as an `enum` list inside
the property, but it writes an enum class as a `$ref` into `$defs`. A test
checks that no published schema contains `$defs`.

## Considered options

**A curated description of each parameter.** A hand-written list of names,
types, ranges and labels. It is simpler to read, but it is a second
declaration that must agree with the validator. JSON Schema is also a standard
that a browser can use for form generation and input checks as it is.

**One catalogue call for everything a front-end can choose.** Variants belong
to the engine and computer difficulties to the session layer. A catalogue call
would make one layer know the other's concepts. A web handler composes its own
response from both.

## Consequences

The schema is a published contract, so changing it can break a front-end.
Each variant's schema is pinned by a test, and a change to it must be made on
purpose.
