"""Hypothesis profiles: quick by default, `--hypothesis-profile=thorough` for depth."""

from hypothesis import settings

settings.register_profile("quick", max_examples=25)
settings.register_profile("thorough", max_examples=400)
settings.load_profile("quick")
