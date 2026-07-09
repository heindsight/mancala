import pytest

from mancala import variants


def test_available_lists_both_variants_sorted() -> None:
    assert variants.available() == ("kalah", "oware")


def test_get_returns_the_named_variant() -> None:
    assert variants.get("kalah").name == "kalah"
    assert variants.get("oware").name == "oware"


def test_get_rejects_unknown_variants() -> None:
    with pytest.raises(ValueError, match="kalah, oware"):
        variants.get("senet")
