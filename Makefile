.PHONY: ruff-check format typecheck lint test pre-commit-setup pre-commit-run

ruff-check:
	uv run ruff check
	uv run ruff format --diff

format:
	uv run ruff format
	uv run ruff check --fix

typecheck:
	uv run ty check

lint: ruff-check typecheck

ARGS=--cov
test:
	uv run pytest $(ARGS)

pre-commit-setup:
	pre-commit install --install-hooks

pre-commit-run:
	pre-commit run --all-files
