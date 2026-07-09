# Mancala

Mancala family board games — a modern resurrection of an ancient student
project. Immutable game engine (Kalah and Oware) plus a terminal interface
for hot-seat play.

## Play

    uv run mancala --variant kalah Heinrich Nora

## Develop

    uv run pytest
    uv run ruff check .
    uv run ruff format .
    uv run ty check

Design docs live in `docs/superpowers/specs/`.
