# Mancala

Mancala family board games — a modern resurrection of an ancient student
project. Immutable game engine (Kalah and Oware) plus a terminal interface
for hot-seat play or play against the computer.

## Play

    uv run mancala --variant kalah Heinrich Nora

Name a seat `cpu:<difficulty>` (`easy`, `medium`, or `hard`) to hand it to the
computer — either seat, or both:

    uv run mancala Heinrich cpu:hard
    uv run mancala cpu:easy cpu:hard

## Develop

    uv run pytest
    uv run ruff check .
    uv run ruff format .
    uv run ty check

Design docs live in `docs/superpowers/specs/`.
