# Configured rules instances and variant descriptors

A variant's `Rules` is constructed with its config and carries it.
`initial_state` takes no arguments. A registry holds one descriptor per
variant: its identifier, its display name, its config model, and a factory.
Identity belongs to the descriptor, so `Rules` has no name.

This replaces stateless singletons. Before, each rules object carried its own
name, and `initial_state` took a seeds-per-cup argument that every variant
accepted. Oware refused every value but four. So a front-end had to know which
arguments each variant would refuse.

A rules object is still immutable. It holds nothing about the game in
progress. One instance can still serve a match and a search at the same time,
as ADR 0000 requires.

## Descriptors parse their own options

A descriptor creates rules from a plain mapping of options, not from a config
object:

```python
def create(self, options: Mapping[str, Any] | None = None) -> Rules:
    return self.factory(self.config_model.model_validate(options or {}))
```

The variant's own config model parses the mapping. It refuses any option it
does not declare. `create` accepts no config object, so a caller cannot give a
`KalahConfig` to Oware. A caller that gives Oware Kalah's options as a mapping
is refused.

This is also the path a front-end takes. It starts from command-line arguments
or JSON, looks up the variant by identifier, builds a mapping, and calls
`create`.

## `config` is a read-only property

The `Rules` protocol declares `config` as a read-only property, not as an
attribute. A protocol attribute is invariant. With `config: BaseModel`, each
variant would have to accept any `BaseModel` written to it, and no variant
does. A read-only property is covariant, so Kalah can return its own
`KalahConfig`.

Declare any future protocol member that is typed as a base class the same way.

## Considered options

**Generic descriptors, `VariantDescriptor[ConfigT]`.** A prototype showed this
does not help. Both real lookups start from a string at runtime: a
command-line argument and a save file. The type checker cannot know which
config type such a lookup returns, so it cannot catch a mismatch there. The
registry cannot hold generic descriptors either:
`dict[str, VariantDescriptor[BaseModel]]` is refused because the type
parameter is invariant, which forces `Any`. Parsing inside `create` catches the
mismatch at runtime instead, in the one place every caller goes through.

**`create` taking a config object.** A caller could then build one variant's
config and give it to another variant's descriptor. The type checker cannot
catch this, for the reason above.

## Consequences

The factory is typed `Callable[[Any], Rules]`. `Kalah` accepts only a
`KalahConfig`, so it cannot satisfy a callable declared to take any
`BaseModel`. `create` is the only caller. It always passes an instance of the
descriptor's own config model.

`Rules` no longer says which variant it is. Code that needs to know, such as
saving a game, is given the descriptor together with the match.
