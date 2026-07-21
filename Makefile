.PHONY: help install-uv install-dev install lint lint-fix test clean

help:
	@echo "Available targets:"
	@echo "  install-uv    Install uv (if not already present)"
	@echo "  install-dev   Install development dependencies"
	@echo "  install       Install production dependencies"
	@echo "  lint          Run ruff check and format check"
	@echo "  lint-fix      Run ruff check --fix and apply formatting"
	@echo "  test          Run unit tests with coverage"
	@echo "  clean         Remove test/coverage artifacts"

install-uv:
	curl -LsSf https://astral.sh/uv/0.11.28/install.sh | sh

install-dev: install-uv
	uv sync
	uv run pre-commit install

install: install-uv
	uv sync --no-dev
	uv run pre-commit install

lint:
	uv run ruff check app tests
	uv run ruff format app tests --check

lint-fix:
	uv run ruff check app tests --fix
	uv run ruff format app tests

test:
	uv run coverage run -m unittest discover -s tests -t . -p "test_*.py"
	uv run coverage report -m
	uv run coverage html -d coverage
	uv run coverage xml

clean:
	rm -rf .coverage coverage coverage.xml .ruff_cache
