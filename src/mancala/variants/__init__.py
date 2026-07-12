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
