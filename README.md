# Mancala

Mancala family board games — a modern resurrection of an ancient student
project. Immutable game engine (Kalah and Oware) plus a terminal interface
for hot-seat play or play against the computer.

## Play

    uv run mancala new --variant kalah Heinrich Nora

## Save & resume

Type `save FILE` instead of a cup number to save the game and exit. Resume
it later with:

    uv run mancala resume FILE

A save file records the variant, player names, current position, and the
full move history; on load the history is replayed and validated before
play resumes.

Name a seat `cpu:<difficulty>` (`easy`, `medium`, or `hard`) to hand it to the
computer — either seat, or both:

    uv run mancala new Heinrich cpu:hard
    uv run mancala new cpu:easy cpu:hard

## Develop

    uv run pytest
    uv run ruff check .
    uv run ruff format .
    uv run ty check

Design docs live in `docs/superpowers/specs/`.
