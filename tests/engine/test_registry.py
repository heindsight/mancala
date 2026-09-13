import pytest

from mancala.engine import variants
from mancala.engine.variants.kalah import Kalah
from mancala.engine.variants.oware import Oware


def test_available_lists_both_variants_sorted() -> None:
    assert variants.available() == ("kalah", "oware")


def test_get_returns_the_registered_singleton_for_each_name() -> None:
    assert isinstance(variants.get("kalah"), Kalah)
    assert isinstance(variants.get("oware"), Oware)
    # The registry hands back one shared stateless instance, not a fresh copy.
    assert variants.get("kalah") is variants.get("kalah")


def test_get_rejects_unknown_variants_and_lists_the_available_ones() -> None:
    with pytest.raises(ValueError, match="unknown variant 'senet'") as excinfo:
        variants.get("senet")
    assert str(excinfo.value) == "unknown variant 'senet'; available: kalah, oware"
