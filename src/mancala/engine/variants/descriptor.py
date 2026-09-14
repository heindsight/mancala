"""The variant descriptor: a variant's identity and configuration surface."""

from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

from pydantic import BaseModel

from mancala.engine.rules import Rules


class VariantDescriptor(NamedTuple):
    """What a front-end reads to offer a variant, and how it creates one.

    `create` takes a plain mapping, not a config object. This variant's own
    `config_model` parses the mapping and refuses options it does not declare.
    So another variant's config cannot be given to this one.

    `factory` accepts `Any`. A constructor that takes only its own config model
    cannot satisfy a callable declared to take any `BaseModel`.
    """

    id: str
    display_name: str
    config_model: type[BaseModel]
    factory: Callable[[Any], Rules]

    def create(self, options: Mapping[str, Any] | None = None) -> Rules:
        """Rules configured by `options`.

        Raises pydantic's `ValidationError`, a `ValueError`, when an option is
        out of range or not one this variant declares.
        """
        return self.factory(self.config_model.model_validate(options or {}))

    def schema(self) -> dict[str, Any]:
        """The published JSON Schema of everything that may be configured."""
        return self.config_model.model_json_schema()
