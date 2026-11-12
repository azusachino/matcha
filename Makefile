.PHONY: check fmt lint types test build

check: fmt-check lint types test

fmt:
	uv run ruff format src tests

fmt-check:
	uv run ruff format --check src tests

lint:
	uv run ruff check src tests

types:
	uv run mypy

test:
	uv run pytest

build:
	uv build
