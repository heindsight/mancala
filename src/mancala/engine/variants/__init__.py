"""Game variant implementations and their registry."""

from mancala.engine.variants import kalah, oware
from mancala.engine.variants.descriptor import VariantDescriptor

_REGISTRY: dict[str, VariantDescriptor] = {
    descriptor.id: descriptor for descriptor in (kalah.DESCRIPTOR, oware.DESCRIPTOR)
}


def get(variant_id: str) -> VariantDescriptor:
    try:
        return _REGISTRY[variant_id]
    except KeyError:
        raise ValueError(
            f"unknown variant {variant_id!r}; available: {', '.join(sorted(_REGISTRY))}"
        ) from None


def available() -> tuple[VariantDescriptor, ...]:
    """Every variant's descriptor, ordered by identifier."""
    return tuple(_REGISTRY[variant_id] for variant_id in sorted(_REGISTRY))
