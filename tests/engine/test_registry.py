import pytest
from pydantic import ValidationError

from mancala.engine import variants


def test_available_publishes_each_variant_with_its_display_name() -> None:
    assert [(d.id, d.display_name) for d in variants.available()] == [
        ("kalah", "Kalah"),
        ("oware", "Oware"),
    ]


def test_get_returns_the_descriptor_for_the_named_variant() -> None:
    assert variants.get("oware").id == "oware"


def test_rules_created_without_options_use_the_default_config() -> None:
    rules = variants.get("kalah").create()
    assert rules.initial_state().board == ((4,) * 6, (4,) * 6)


def test_rules_are_created_with_the_requested_options() -> None:
    rules = variants.get("kalah").create({"seeds_per_cup": 6})
    assert rules.initial_state().board == ((6,) * 6, (6,) * 6)


def test_created_rules_carry_their_config() -> None:
    rules = variants.get("kalah").create({"seeds_per_cup": 3})
    assert rules.config.model_dump() == {"seeds_per_cup": 3}


def test_a_variant_with_nothing_to_configure_has_an_empty_config() -> None:
    assert variants.get("oware").create().config.model_dump() == {}


@pytest.mark.parametrize("seeds", [2, 7])
def test_an_out_of_range_option_is_refused(seeds: int) -> None:
    with pytest.raises(ValidationError, match="seeds_per_cup"):
        variants.get("kalah").create({"seeds_per_cup": seeds})


def test_an_option_belonging_to_another_variant_is_refused() -> None:
    with pytest.raises(ValidationError, match="seeds_per_cup"):
        variants.get("oware").create({"seeds_per_cup": 4})


@pytest.mark.parametrize("variant_id", [d.id for d in variants.available()])
def test_every_variant_refuses_an_unknown_option(variant_id: str) -> None:
    with pytest.raises(ValidationError, match="cups_per_side"):
        variants.get(variant_id).create({"cups_per_side": 7})


# The published schema is a contract with front-ends that read it directly, so
# each variant's is pinned here: a dependency upgrade that changes the output
# fails this test rather than a browser. Update a snapshot only on purpose.
PUBLISHED_SCHEMAS = {
    "kalah": {
        "additionalProperties": False,
        "description": "Settings for one game of Kalah.",
        "properties": {
            "seeds_per_cup": {
                "default": 4,
                "description": "How many seeds each cup holds when the game starts.",
                "maximum": 6,
                "minimum": 3,
                "title": "Seeds per cup",
                "type": "integer",
            },
        },
        "title": "KalahConfig",
        "type": "object",
    },
    "oware": {
        "additionalProperties": False,
        "description": "Settings for one game of Oware. It has nothing to configure.",
        "properties": {},
        "title": "OwareConfig",
        "type": "object",
    },
}


def test_every_variant_has_a_pinned_schema() -> None:
    assert [d.id for d in variants.available()] == list(PUBLISHED_SCHEMAS)


@pytest.mark.parametrize(("variant_id", "schema"), PUBLISHED_SCHEMAS.items())
def test_each_variant_publishes_its_pinned_schema(
    variant_id: str, schema: dict[str, object]
) -> None:
    assert variants.get(variant_id).schema() == schema


@pytest.mark.parametrize("variant_id", PUBLISHED_SCHEMAS)
def test_each_published_schema_is_flat(variant_id: str) -> None:
    # Categorical settings must be inline literals: an enum type would emit
    # `$defs` and make every reader resolve cross-references.
    assert "$defs" not in variants.get(variant_id).schema()


def test_get_rejects_unknown_variants_and_lists_the_available_ones() -> None:
    with pytest.raises(ValueError, match="unknown variant 'senet'") as excinfo:
        variants.get("senet")
    assert str(excinfo.value) == "unknown variant 'senet'; available: kalah, oware"
