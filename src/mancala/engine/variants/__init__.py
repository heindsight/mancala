"""Game variant implementations and their registry."""

from mancala.engine.rules import Rules
from mancala.engine.variants._common import CUPS as CUPS
from mancala.engine.variants.kalah import Kalah
from mancala.engine.variants.oware import Oware

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
