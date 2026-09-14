# Configured rules instances and variant descriptors

Rules used to be stateless singletons. Each one carried its own name, and
`initial_state` took a seeds-per-cup argument that every variant accepted.
Oware refused every value but four, so a front-end had to know which arguments
each variant would refuse.

Now a variant's `Rules` is constructed with its config and carries it, and
`initial_state` takes no arguments. A registry holds one descriptor per
variant: its identifier, its display name, its config model, and a factory.
Identity belongs to the descriptor, so `Rules` has no name.

A rules object is still immutable and holds nothing about the game in
progress. One instance can still serve a match and a search at the same time,
as ADR 0000 requires.

## Descriptors parse their own options

A descriptor creates rules from a plain mapping of options, not from a config
object:

```python
def create(self, options: Mapping[str, Any] | None = None) -> Rules:
    return self.factory(self.config_model.model_validate(options or {}))
```

The variant's own config model parses the mapping and refuses any setting it
does not declare. So Kalah's settings cannot be handed to Oware: the mistake
cannot be expressed, rather than merely being discouraged. This is also the
path a front-end takes: arguments or JSON, then an identifier, then a mapping,
then `create`.

## `config` is a read-only property

The `Rules` protocol declares `config` as a read-only property. A protocol
attribute is invariant. `config: BaseModel` would require each variant to accept
any `BaseModel` written to it, and no variant does. A property is covariant, so
Kalah can return its own `KalahConfig`. The same applies to any future protocol
member typed as a base class.

## Considered options

**Generic descriptors, `VariantDescriptor[ConfigT]`.** Prototyped and rejected.
Both real lookups start from a string at runtime: a command-line argument and a
save file. So the type parameter is erased exactly where it would catch a
mismatch. The registry cannot hold the bound either:
`dict[str, VariantDescriptor[BaseModel]]` is refused under invariance, which
forces `Any`. Parsing inside `create` closes the gap that generics could not.

**`create` taking a config object.** This lets a caller build one variant's
config and hand it to another variant's descriptor. The type checker cannot
catch it, for the reason above.

## Consequences

The factory is typed `Callable[[Any], Rules]`. `Kalah` accepts only a
`KalahConfig`, so it cannot satisfy a callable declared to take any
`BaseModel`. `create` is the only caller, and it passes the factory an instance
of the descriptor's own config model.

Code that needs a variant's identity, such as saving a game, is handed the
descriptor alongside the match. `Rules` no longer answers that question.
