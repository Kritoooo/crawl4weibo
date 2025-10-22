# Crawl4Weibo Architecture Analysis

## Executive Summary

**Crawl4Weibo** is a professional Weibo crawler library built in Python that simulates mobile requests and handles anti-scraping strategies. It uses **synchronous HTTP requests** (via `requests` library) with built-in rate limiting and proxy support. The architecture is modular with clear separation between client, utilities, models, and exception handling.

---

## 1. Main Client/Crawler Implementation

### Primary Entry Point: `WeiboClient`
**Location:** `/home/buyunfeng/demo/crawl4weibo/crawl4weibo/crawl4weibo/core/client.py`

The `WeiboClient` is the main crawler class with the following characteristics:

- **HTTP Framework:** Uses `requests.Session()` (synchronous, not async)
- **Architecture:** Single-threaded, synchronous request model
- **Key Components:**
  - `requests.Session` - HTTP client
  - `WeiboParser` - Response parser
  - `ImageDownloader` - Image download utility
  - `ProxyPool` - Proxy management system

### Core Methods
```python
# User operations
get_user_by_uid(uid)                  # Fetch user profile
get_user_posts(uid, page, expand)     # Get user timeline
get_post_by_bid(bid)                  # Get single post details

# Search operations
search_users(query, page, count)      # Search for users
search_posts(query, page)              # Search for posts

# Image operations
download_post_images(post)            # Download from single post
download_posts_images(posts)          # Batch download
download_user_posts_images(uid, pages) # Download user's posts
```

---

## 2. Crawling Architecture: Sync with Rate Limiting

### Request Model
**Synchronous (NOT Async)**
- Uses `requests.Session.get()` for all HTTP calls
- Single-threaded execution
- No async/await patterns used
- Sequential request processing

### Rate Limiting Strategy

**Built-in Delays:**
```python
# In get_user_posts() (line 258):
time.sleep(random.uniform(1, 3))

# In search_users() (line 323):
time.sleep(random.uniform(1, 3))

# In search_posts() (line 362):
time.sleep(random.uniform(1, 3))

# In download_user_posts_images() (line 461):
if page < pages:
    time.sleep(random.uniform(2, 4))
```

**Between Image Downloads:**
```python
# In download_post_images() (line 166):
delay = random.uniform(*self.delay_range)  # default (1.0, 3.0)
time.sleep(delay)
```

**Retry Backoff:**
```python
# In _request() (line 166):
if response.status_code == 432:  # anti-crawler block
    sleep_time = random.uniform(4, 7)
    time.sleep(sleep_time)  # Exponential backoff
```

### 432 Anti-Crawler Handling
- Detects HTTP 432 responses (Weibo's anti-crawler protection)
- Implements 4-7 second backoff on 432 errors
- Retries up to `max_retries` times (default: 3)
- Raises `NetworkError` if all retries exhausted

---

## 3. Main Entry Points for Crawling

### Direct Client Usage
```python
# Entry point 1: Direct instantiation
from crawl4weibo import WeiboClient

client = WeiboClient()  # Initialize with defaults
user = client.get_user_by_uid("2656274875")  # Fetch user
posts = client.get_user_posts("2656274875", page=1)  # Fetch posts
```

### Entry Points by Functionality

| Entry Point | Purpose | Returns | Rate Limit |
|-----------|---------|---------|-----------|
| `get_user_by_uid(uid)` | User profile + stats | `User` object | implicit (no delay in method) |
| `get_user_posts(uid, page, expand)` | User timeline | `List[Post]` | 1-3 sec pre-request |
| `get_post_by_bid(bid)` | Single post full content | `Post` object | implicit |
| `search_users(query, page, count)` | User search | `List[User]` | 1-3 sec pre-request |
| `search_posts(query, page)` | Post search | `List[Post]` | 1-3 sec pre-request |
| `download_post_images(post)` | Image download from post | `Dict[url -> filepath]` | 1-3 sec between images |
| `download_user_posts_images(uid, pages)` | Batch user post images | `Dict[post_id -> Dict[url -> filepath]]` | 2-4 sec between pages |

### Example Entry Point Flow
```
WeiboClient() 
  ├─ __init__() sets up:
  │   ├─ requests.Session (HTTP client)
  │   ├─ WeiboParser (JSON parser)
  │   ├─ ImageDownloader (download utility)
  │   ├─ ProxyPool (proxy management)
  │   └─ Mobile User-Agent headers
  │
  ├─ get_user_by_uid(uid)
  │   ├─ _request() with 3x max_retries
  │   ├─ parser.parse_user_info()
  │   └─ return User object
  │
  └─ get_user_posts(uid, page)
      ├─ time.sleep(1-3 sec) [RATE LIMIT]
      ├─ _request() with 3x max_retries
      ├─ parser.parse_posts()
      └─ return List[Post]
```

---

## 4. Configuration Options for Crawl Speed Control

### Client Initialization Parameters
```python
WeiboClient(
    cookies: Optional[Union[str, Dict[str, str]]] = None,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    user_agent: Optional[str] = None,
    proxy_api_url: Optional[str] = None,
    proxy_api_parser: Optional[Callable] = None,
    dynamic_proxy_ttl: int = 300,          # ← SPEED CONTROL
    proxy_pool_size: int = 10,             # ← SPEED CONTROL
    proxy_fetch_strategy: str = "random",  # ← SPEED CONTROL
)
```

### Speed Control Mechanisms

#### 1. **Proxy Configuration**
```python
# Dynamic proxies to avoid rate limits
client = WeiboClient(
    proxy_api_url="http://api.proxy.com/get?format=json",
    dynamic_proxy_ttl=300,      # Proxy rotation every 5 min
    proxy_pool_size=10,         # Maintain 10 proxies in pool
    proxy_fetch_strategy="random"  # or "round_robin"
)

# Manual proxy addition
client.add_proxy("http://1.2.3.4:8080", ttl=600)  # 10 min TTL
```

#### 2. **Image Downloader Configuration**
```python
ImageDownloader(
    session=session,
    download_dir="./weibo_images",
    max_retries=3,              # Retry count for failed downloads
    delay_range=(1.0, 3.0),     # Random delay between images
)
```

#### 3. **Request Retry Configuration**
```python
def _request(
    self,
    url: str,
    params: Dict,
    max_retries: int = 3,       # ← Configurable
    use_proxy: bool = True,     # ← Can disable proxy per request
) -> Dict[str, Any]:
```

#### 4. **Per-Method Speed Control**
- No built-in parameters to adjust internal delays
- Delays are **hardcoded** in methods:
  - `get_user_posts()`: 1-3 sec (hardcoded)
  - `search_users()`: 1-3 sec (hardcoded)
  - `search_posts()`: 1-3 sec (hardcoded)
  - Image downloads: 1-3 sec between images (hardcoded)
  - Page pagination: 2-4 sec between pages (hardcoded)

### Proxy Pool Management API
```python
client.add_proxy(proxy_url, ttl=None)        # Add static proxy
client.get_proxy_pool_size()                 # Check pool size
client.clear_proxy_pool()                    # Clear all proxies

# Proxy selection strategies
ProxyPoolConfig(fetch_strategy="random")     # Random selection
ProxyPoolConfig(fetch_strategy="round_robin") # Round-robin
```

---

## 5. Existing Test Files

### Test Coverage
**Location:** `/home/buyunfeng/demo/crawl4weibo/crawl4weibo/tests/`

```
tests/
├── test_client.py           (4.6 KB) - Unit tests for WeiboClient
├── test_integration.py      (5.4 KB) - Integration tests (real API calls)
├── test_downloader.py       (8.8 KB) - Image downloader tests
├── test_models.py           (3.0 KB) - Data model tests
├── test_proxy.py            (12.1 KB) - Proxy pool tests
└── __init__.py
```

### Test Markers and Categorization
```python
@pytest.mark.unit          # Unit tests (mocked, no external calls)
@pytest.mark.integration   # Integration tests (real API calls)
@pytest.mark.slow          # Slow running tests
```

### Test File Summaries

#### **test_client.py** (5 unit tests + 2 integration tests)
- `test_client_initialization()` - Basic client setup
- `test_client_methods_exist()` - Method existence check
- `test_client_with_proxy_initialization()` - Proxy setup
- `test_add_proxy_to_client()` - Manual proxy addition
- `test_request_uses_proxy_when_enabled()` - Proxy usage verification
- `test_request_without_proxy_when_disabled()` - Proxy disable test

#### **test_integration.py** (9 real API integration tests)
- `test_get_user_by_uid_returns_data()` - Real user fetch
- `test_get_user_posts_returns_data()` - Real posts fetch
- `test_get_user_posts_with_expand_returns_data()` - Long text expansion
- `test_get_post_by_bid_returns_data()` - Single post fetch
- `test_search_users_returns_data()` - User search
- `test_search_posts_returns_data()` - Post search
- `test_client_handles_invalid_uid()` - Error handling
- `test_client_handles_empty_search_results()` - Empty results handling

#### **test_downloader.py** (Image downloader tests)
- `test_downloader_initialization()` - Setup test
- `test_generate_filename()` - Filename generation
- `test_download_image_success()` - Successful download
- `test_download_image_non_image_content()` - Content type validation
- `test_download_image_network_error()` - Network error handling
- `test_download_post_images()` - Batch post image download

#### **test_proxy.py** (Proxy pool tests)
- `test_default_config()` - Default proxy config
- `test_add_static_proxy_without_ttl()` - Static proxy addition
- `test_add_static_proxy_with_ttl()` - Proxy TTL expiration
- `test_proxy_round_robin_rotation()` - Round-robin strategy
- `test_proxy_random_selection()` - Random strategy
- `test_clean_expired_proxies()` - Expiration cleanup
- Plus 6+ more tests for dynamic API, pool size limits, etc.

#### **test_models.py**
- Model serialization/deserialization tests
- Data model conversion tests

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific marker
uv run pytest -m unit              # Only unit tests
uv run pytest -m integration       # Only integration tests

# Run specific file
uv run pytest tests/test_client.py

# With coverage
uv run pytest --cov=crawl4weibo
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   WeiboClient                               │
│  (Synchronous HTTP crawler with rate limiting)              │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
    ┌─────────┐      ┌──────────────┐    ┌────────────┐
    │requests │      │WeiboParser   │    │ProxyPool   │
    │Session  │      │(JSON/HTML)   │    │(Proxy Mgmt)│
    └─────────┘      └──────────────┘    └────────────┘
        │                   │                   │
        │ 1-3 sec delay   Parses to:          │ Dynamic/Static
        │ (built-in)      │                    │ Round-robin/Random
        │                 ├─ User model        │ TTL expiration
        ▼                 ├─ Post model        │ Pool size limit
    ┌─────────────────┐   └─ Exceptions       ▼
    │HTTP Endpoints   │   ┌──────────────┐
    │ m.weibo.cn API  │   │ImageDownloader
    │ (mobile mock)   │   │ · max_retries
    └─────────────────┘   │ · delay_range
                          │ · duplicate detection
                          └──────────────────┘

Rate Limiting Points:
• Pre-request: 1-3 sec (get_user_posts, search_*)
• Pre-page: 2-4 sec (between pagination)
• Pre-image: 1-3 sec (between image downloads)
• 432 error: 4-7 sec backoff (retry)
• Retry backoff: 2-5 sec (network errors)
```

---

## Key Characteristics for Performance Testing

### Synchronous Behavior
- **Single-threaded execution** - requests are sequential
- **No concurrency** - each operation waits for previous to complete
- **Predictable delays** - random.uniform() between min/max values

### Rate Limiting
- **Implicit delays** - built into method calls (not configurable)
- **Exponential backoff** - responds to 432 anti-crawler blocks
- **Per-request proxy** - can use different proxy for each request

### Testable Aspects
1. **Throughput**: Requests/sec with various proxy configurations
2. **Latency**: Response time per operation (includes internal delays)
3. **Error recovery**: Behavior on 432 blocks and network failures
4. **Resource usage**: Memory/CPU under sustained load
5. **Proxy effectiveness**: Success rate with/without proxies
6. **Image download**: Throughput with batch downloads

### Constraints for Stress Testing
- **No built-in concurrency** - must handle with external threading/multiprocessing
- **Hardcoded delays** - cannot be overridden without code modification
- **Single proxy per request** - rotation via ProxyPool is sequential
- **Max 3 retries** - configurable per _request() call
- **No timeout configuration** - fixed 5 sec timeout in code

---

## Project Dependencies

**Core Dependencies** (pyproject.toml):
- `requests>=2.25.0` - HTTP client
- `lxml>=4.6.0` - HTML parsing
- `tqdm>=4.60.0` - Progress bars
- `python-dateutil>=2.8.0` - Date parsing

**Dev Dependencies**:
- `pytest>=7.4.4` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `responses>=0.25.8` - HTTP mocking
- `ruff>=0.14.0` - Code linting/formatting

---

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `core/client.py` | 466 | Main WeiboClient class |
| `utils/proxy.py` | 189 | ProxyPool management |
| `utils/downloader.py` | 276 | Image download utility |
| `utils/parser.py` | 150+ | JSON/HTML parsing |
| `models/user.py` | - | User data model |
| `models/post.py` | 87 | Post data model |
| `exceptions/base.py` | - | Custom exceptions |
| `tests/test_client.py` | 148 | Client unit tests |
| `tests/test_integration.py` | 171 | Integration tests |
| `tests/test_proxy.py` | 350+ | Proxy pool tests |
| `tests/test_downloader.py` | 200+ | Downloader tests |

---

## Recommendations for Performance/Stress Testing

1. **Test Framework**: Use `concurrent.futures.ThreadPoolExecutor` or `asyncio` wrapper to parallelize the synchronous client

2. **Metrics to Capture**:
   - Requests per second (RPS)
   - Average latency per operation
   - 95th/99th percentile response times
   - Error rates (4xx, 5xx, network timeouts)
   - 432 error frequency and recovery time
   - Proxy pool hit rate

3. **Test Scenarios**:
   - Single client sustained load
   - Multiple concurrent clients
   - Mixed operation types (user fetch, posts, search, downloads)
   - Network failure simulation
   - Proxy rotation effectiveness
   - Rate limit handling

4. **Known Limitations**:
   - Synchronous design limits concurrency
   - Hardcoded delays cannot be adjusted dynamically
   - 5-second timeout is fixed
   - No async support requires external parallelization

