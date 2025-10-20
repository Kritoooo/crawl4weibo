# Repository Guidelines

## Project Structure & Module Organization
The library code lives in `crawl4weibo/`, with `core/` managing request orchestration and retry logic, `models/` exposing typed results, `utils/` housing shared helpers, and `exceptions/` defining recoverable error types. Tests mirror runtime modules inside `tests/`, living assets and walkthroughs are under `docs/` and `examples/` (start with `examples/simple_example.py` for a smoke run).

## Build, Test, and Development Commands
- `uv sync --dev` Install project and development extras into the local uv-managed virtualenv.
- `uv run python examples/simple_example.py` Run the basic crawling demo against live data.
- `uv run pytest` Execute the full suite (markers: `unit`, `integration`, `slow`).
- `uv run pytest -m "unit and not slow"` Run a fast gate before opening a PR.
- `uv run ruff check crawl4weibo --fix && uv run ruff format crawl4weibo` Enforce linting, import order, and formatting defaults.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation, 88-character lines, and double-quoted strings (ruff enforces these). Prefer descriptive `snake_case` for functions and attributes, keep constants uppercase, and leave response keys unchanged to reflect upstream payloads. Add type hints on new public APIs and keep IO-heavy logic inside `core/` helpers so models remain lightweight.

## Testing Guidelines
Place new tests in `tests/` using the `test_*.py` pattern and `Test*` classes. Mark slow or network-consuming flows with `@pytest.mark.slow` or `@pytest.mark.integration` so they can be filtered. Prefer running suites through `uv run pytest` so the same environment is used locally and in CI. Cover both success and failure paths for request handlers, and include fixtures or notes when relying on real Weibo calls. Aim for meaningful coverage that exercises serialization and retry behavior rather than chasing a fixed percentage.

## Commit & Pull Request Guidelines
Use Conventional Commit style subjects (`feat:`, `fix:`, `docs:`) in the imperative, under 72 characters, mirroring existing history. Each PR should describe the change, call out API or behavior impacts, link any tracked issues, and attach test evidence (`pytest`, `ruff`, or demos). Request reviews early for changes touching rate-limiting or authentication to ensure shared understanding before merge.
