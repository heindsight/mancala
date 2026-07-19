# Mancala

Mancala family board games — a modern resurrection of an ancient student
project. Immutable game engine (Kalah and Oware) plus a terminal interface
for hot-seat play or play against the computer.

## Play

    uv run mancala --variant kalah Heinrich Nora

Or take on the computer at `easy`, `medium`, or `hard`:

    uv run mancala --computer hard Heinrich

## Develop

    uv run pytest
    uv run ruff check .
    uv run ruff format .
    uv run ty check

Design docs live in `docs/superpowers/specs/`.
