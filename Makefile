.PHONY: check fmt lint test build

check: fmt-check lint test

fmt:
	uv run ruff format src tests

fmt-check:
	uv run ruff format --check src tests

lint:
	uv run ruff check src tests

test:
	uv run pytest

build:
	uv build
