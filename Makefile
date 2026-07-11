.PHONY: ruff-check format typecheck lint test

ruff-check:
	uv run ruff check --unsafe-fixes --show-fixes
	uv run ruff format --diff

format:
	uv run ruff format
	uv run ruff check --fix --unsafe-fixes --show-fixes

typecheck:
	uv run ty check

lint: ruff-check typecheck

ARGS=--cov
test:
	uv run pytest $(ARGS)
