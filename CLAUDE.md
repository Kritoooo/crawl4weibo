# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crawl4Weibo is a production-ready Python library for scraping Weibo (微博) mobile web data. It handles anti-scraping mechanisms (including "432 protection"), manages proxy pools, and returns structured data models. Browser-based cookie acquisition using Playwright is the default approach for bypassing anti-scraping.

## Development Commands

### Setup and Installation
```bash
uv sync --dev                          # Install all dependencies (including Playwright)
uv run playwright install chromium     # Install Chromium browser
```

### Testing
```bash
uv run pytest                          # Run all tests
uv run pytest -m "unit and not slow"   # Fast tests only (pre-PR gate)
uv run pytest tests/test_proxy.py -v   # Specific test file
uv run pytest tests/test_proxy.py::TestProxyPool::test_batch_proxy_fetch_multiple_proxies  # Single test
```

Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`

### Code Quality
```bash
uv run ruff check crawl4weibo --fix    # Lint and auto-fix
uv run ruff format crawl4weibo         # Format code
```

### Examples
```bash
uv run python examples/simple_example.py              # Basic usage
uv run python examples/download_images_example.py     # Image download demo
```

See `examples/` directory for more usage examples.

## Architecture

### Module Organization

```
crawl4weibo/
├── core/          # Request orchestration and retry logic
│   └── client.py  # WeiboClient - main entry point
├── models/        # Typed data models (User, Post)
├── utils/         # Shared utilities
│   ├── parser.py         # WeiboParser - JSON to model conversion
│   ├── proxy.py          # ProxyPool - proxy management
│   ├── proxy_parsers.py  # Proxy API response parsers
│   ├── cookie_fetcher.py # Browser/requests-based cookie acquisition
│   ├── rate_limit.py     # Rate limiting configuration
│   └── downloader.py     # ImageDownloader - batch image fetching
└── exceptions/    # Business-level exceptions
    └── base.py
```

### Core Request Flow

1. **WeiboClient** initializes session with browser-based cookie fetching (Playwright)
2. **_request()** handles HTTP calls with exponential backoff retry (handles 432 protection)
3. **WeiboParser** converts raw JSON to typed User/Post models
4. **ProxyPool** manages proxy lifecycle (pooling or one-time mode)
5. **RateLimiter** adjusts delays based on proxy pool size

### Key Design Patterns

**Proxy Pool Architecture**
- **Pooling mode** (default): Caches proxies with TTL, reuses across requests
- **One-time mode** (`use_once_proxy=True`): Fetches fresh proxy for each request
  - Uses internal buffer to efficiently consume batch API responses
  - Ideal for providers that charge per IP count
  - Example: API returns 10 IPs → uses all 10 before next API call

**Retry Strategy**
- Exponential backoff with jitter in `WeiboClient._request()`
- Special handling for 432 status codes (anti-scraping)
- Retry wait times vary by proxy mode:
  - **One-time proxy**: No wait (immediate retry with fresh IP)
  - **Pooled proxy**: 0.5-1.5s wait
  - **No proxy**: 2-7s wait

**Rate Limiting**
- Automatically adjusts delays based on proxy pool size
- Larger pool → shorter delays (more IPs available)
- Smaller pool → longer delays (avoid IP bans)
- Per-method multipliers supported via `method_multipliers`

## Testing Guidelines

### General Principles

- Place tests in `tests/` mirroring module structure
- Use `@responses.activate` for mocking HTTP calls
- Mark network-consuming tests with `@pytest.mark.integration`
- **CRITICAL**: Unit tests should NEVER use rate limiting since they mock all external requests

### Rate Limiting in Tests

**Unit tests** must disable rate limiting to avoid unnecessary delays:

```python
# Use the pytest fixture (recommended)
def test_get_user(client_no_rate_limit):
    user = client_no_rate_limit.get_user_by_uid("123")
    assert user is not None

# Or create client manually
def test_something():
    rate_config = RateLimitConfig(disable_delay=True)
    client = WeiboClient(rate_limit_config=rate_config)
    # ... test code
```

**Rate limiting tests** should use minimal delays (50-150ms):

```python
def test_rate_limiting_behavior():
    # ONLY for tests that verify rate limiting logic
    rate_config = RateLimitConfig(
        base_delay=(0.05, 0.1),   # Minimal delay for fast testing
        min_delay=(0.01, 0.03),
        disable_delay=False
    )
    client = WeiboClient(rate_limit_config=rate_config)
    # ... verify rate limiting works
```

**Performance Impact**: Proper rate limit handling improved test performance by **4x** (unit tests: 271s → 67s).

### Pytest Fixtures

The `tests/unit/conftest.py` provides helpful fixtures:

- `client_no_rate_limit` - WeiboClient with rate limiting disabled (use this for most unit tests)
- `client_no_rate_limit_with_proxy` - Client with both rate limiting disabled and proxy configured
- `mock_cookie_fetcher` - Mocked CookieFetcher for testing cookie handling

## Best Practices

### Code Quality

1. **Rate Limiting in Tests**
   - Disable rate limiting in most unit tests using `RateLimitConfig(disable_delay=True)`
   - Use the `client_no_rate_limit` fixture for all tests that don't verify rate limiting behavior
   - Only enable rate limiting when explicitly testing rate limiting logic itself
   - This pattern is critical for maintaining fast test execution (achieved 4x speedup)

2. **Type Hints**
   - Add complete type hints to all functions (parameters and return types)
   - Use `Union[type1, type2]` for functions accepting multiple types
   - Example fixes needed:
     ```python
     # Before
     def default_proxy_parser(response_data) -> list[str]:
     def setup_logger(name="crawl4weibo", level=logging.INFO):

     # After
     def default_proxy_parser(response_data: Union[str, dict]) -> list[str]:
     def setup_logger(name: str = "crawl4weibo", level: int = logging.INFO) -> logging.Logger:
     ```

3. **API Documentation**
   - Document return types in docstrings for complex structures
   - Example:
     ```python
     def parse_proxy_response(response: str) -> list[str]:
         """
         Parse proxy API response into list of proxy URLs.

         Returns:
             list[str]: Proxy URLs in format "http://user:pass@host:port"
         """
     ```

### Common Tasks

**Adding a New Proxy Parser Format**

1. Add parser function to `crawl4weibo/utils/proxy_parsers.py`
2. Update `default_proxy_parser()` to detect new format if needed
3. Add test cases to `tests/test_proxy_parsers.py`
4. Ensure parser returns `List[str]`, not `str`

**Adding a New API Endpoint**

1. Add method to `WeiboClient` in `core/client.py`
2. Use `self._request()` for HTTP calls (includes retry logic)
3. Pass response to `WeiboParser` for data extraction
4. Add corresponding model if new data structure needed
5. Add unit tests with mocked responses (use `client_no_rate_limit`)

**Browser-Based Cookie Fetching**

Browser automation (Playwright) is now **required** and enabled by default:

```python
from crawl4weibo.core.client import WeiboClient

client = WeiboClient()  # Browser mode by default
```

If Playwright is not installed, the client will display installation instructions.

## Code Style

- **Match existing code style**: New code should follow the patterns and conventions used in the existing codebase
- PEP 8 with 88-character lines (enforced by ruff)
- Double-quoted strings
- Type hints on all public APIs
- snake_case for functions/variables

## Commit Guidelines

Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Subject line imperative mood, under 72 characters
- Include test evidence in PR descriptions
- Flag API/behavior changes explicitly
