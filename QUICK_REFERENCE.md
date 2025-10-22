# Crawl4Weibo Quick Reference for Performance Testing

## Key Findings at a Glance

### What Type of Crawler?
- **Synchronous HTTP** (not async)
- **Single-threaded** execution
- **Rate-limited** with hardcoded delays
- **Proxy-aware** with dynamic/static pool support

### Main Client Class
```python
from crawl4weibo import WeiboClient

client = WeiboClient(
    proxy_api_url="http://api.proxy.com/get",     # Optional
    dynamic_proxy_ttl=300,                        # Proxy TTL
    proxy_pool_size=10,                           # Pool capacity
    proxy_fetch_strategy="random"                 # or "round_robin"
)
```

### Core Methods & Built-in Delays

| Method | Built-in Delay | Purpose |
|--------|-----------------|---------|
| `get_user_by_uid(uid)` | None | User profile |
| `get_user_posts(uid, page)` | **1-3 sec** | Timeline |
| `get_post_by_bid(bid)` | None | Post details |
| `search_users(query)` | **1-3 sec** | Search users |
| `search_posts(query)` | **1-3 sec** | Search posts |
| `download_post_images()` | **1-3 sec** (between) | Download images |
| Multi-page downloads | **2-4 sec** (between) | Batch downloads |

### Rate Limiting Strategy
1. **Built-in delays**: Methods include `time.sleep(random.uniform(X, Y))`
2. **Retry backoff**: 4-7 sec on 432 anti-crawler blocks
3. **Network error backoff**: 2-5 sec on failures
4. **Max retries**: 3 attempts (configurable per request)
5. **Request timeout**: 5 seconds (hardcoded)

### HTTP Error Handling
- **HTTP 432**: Weibo's anti-crawler block → backoff 4-7 sec, retry up to 3 times
- **Other errors**: Backoff 2-5 sec, retry up to 3 times
- **Final failure**: Raises `NetworkError` exception

### Configuration for Speed Control

**Limited options**:
- Proxy pool size (default: 10)
- Proxy rotation strategy: `"random"` or `"round_robin"`
- Dynamic proxy TTL (default: 300 sec)
- Manual proxy addition: `client.add_proxy(url, ttl=600)`
- Per-request proxy disabling: `use_proxy=False` parameter

**NOT configurable**:
- Internal delays (1-3, 2-4 sec hardcoded)
- Request timeout (5 sec hardcoded)
- Retry count in specific methods (3 hardcoded in _request)

### Test Files Location
```
/home/buyunfeng/demo/crawl4weibo/crawl4weibo/tests/
├── test_client.py        - Client tests (mocked)
├── test_integration.py   - Real API tests
├── test_downloader.py    - Image download tests
├── test_proxy.py         - Proxy pool tests
└── test_models.py        - Data model tests
```

### Running Tests
```bash
cd /home/buyunfeng/demo/crawl4weibo/crawl4weibo

# All tests
uv run pytest

# Unit tests only (mocked, fast)
uv run pytest -m unit

# Integration tests (real API, slow)
uv run pytest -m integration

# Specific file
uv run pytest tests/test_client.py -v

# With coverage
uv run pytest --cov=crawl4weibo
```

### Performance Testing Challenges

**Limitations to know**:
1. **Synchronous only** - single request at a time
2. **Hardcoded delays** - 1-3 sec minimum between operations
3. **Fixed timeout** - 5 seconds for all requests
4. **Sequential proxy rotation** - not truly parallel
5. **No async support** - requires external threading for parallelization

**Recommended approach**:
```python
from concurrent.futures import ThreadPoolExecutor
import time

def fetch_user(uid):
    client = WeiboClient()  # Create per-thread
    return client.get_user_by_uid(uid)

# Parallel load test
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fetch_user, uid) for uid in uids]
    results = [f.result() for f in futures]
```

### Project Structure
```
crawl4weibo/
├── core/
│   └── client.py           - WeiboClient (main class)
├── utils/
│   ├── proxy.py            - ProxyPool
│   ├── downloader.py       - ImageDownloader
│   ├── parser.py           - WeiboParser
│   └── logger.py           - Logging setup
├── models/
│   ├── user.py             - User model
│   └── post.py             - Post model
├── exceptions/
│   └── base.py             - Custom exceptions
├── __init__.py             - Package exports
└── tests/
    ├── test_client.py
    ├── test_integration.py
    ├── test_downloader.py
    ├── test_proxy.py
    └── test_models.py
```

### Dependencies
- `requests` - HTTP client
- `lxml` - HTML parsing
- `python-dateutil` - Date parsing
- `pytest` - Testing (dev)
- `responses` - HTTP mocking (dev)

### Key Classes & APIs

#### WeiboClient
```python
client = WeiboClient(proxy_api_url="...", proxy_pool_size=10)

# User operations
user = client.get_user_by_uid("2656274875")
posts = client.get_user_posts("2656274875", page=1, expand=True)
post = client.get_post_by_bid("Q6FyDtbQc")

# Search operations
users = client.search_users("新浪", page=1, count=10)
posts = client.search_posts("人工智能", page=1)

# Image operations
results = client.download_post_images(post)
results = client.download_posts_images(posts)
results = client.download_user_posts_images("2656274875", pages=2)

# Proxy management
client.add_proxy("http://1.2.3.4:8080", ttl=600)
size = client.get_proxy_pool_size()
client.clear_proxy_pool()
```

#### ProxyPool
```python
from crawl4weibo.utils.proxy import ProxyPool, ProxyPoolConfig

config = ProxyPoolConfig(
    proxy_api_url="http://api.proxy.com/get",
    dynamic_proxy_ttl=300,
    pool_size=10,
    fetch_strategy="random"  # or "round_robin"
)
pool = ProxyPool(config)

pool.add_proxy("http://1.2.3.4:8080", ttl=600)
proxy_dict = pool.get_proxy()  # Returns {"http": "...", "https": "..."}
size = pool.get_pool_size()
pool.clear_pool()
pool.is_enabled()  # Check if proxy is enabled
```

#### Data Models
```python
from crawl4weibo import User, Post

# User model fields
user.id
user.screen_name
user.followers_count
user.following_count
user.posts_count
user.verified
user.avatar_url

# Post model fields
post.id
post.bid
post.user_id
post.text
post.created_at
post.attitudes_count     # likes
post.comments_count
post.reposts_count
post.pic_urls
post.video_url
post.is_long_text
post.retweeted_status    # for retweets
```

### Exception Types
- `CrawlError` - General crawling error
- `NetworkError` - Network/HTTP errors
- `UserNotFoundError` - User not found
- `ParseError` - Parsing failure
- `RateLimitError` - Rate limited
- `AuthenticationError` - Auth failure

### Mobile User-Agent (Default)
```
Mozilla/5.0 (Linux; Android 13; SM-G9980) 
AppleWebKit/537.36 (KHTML, like Gecko) 
Chrome/112.0.5615.135 Mobile Safari/537.36
```

---

## Quick Test Writing Example

```python
import pytest
from crawl4weibo import WeiboClient

@pytest.mark.unit
def test_client_with_proxy():
    client = WeiboClient(
        proxy_api_url="http://api.proxy.com/get",
        proxy_pool_size=5
    )
    assert client.proxy_pool is not None
    
@pytest.mark.integration
def test_fetch_user():
    client = WeiboClient()
    try:
        user = client.get_user_by_uid("2656274875")
        assert user.screen_name is not None
    except Exception as e:
        pytest.skip(f"API unavailable: {e}")

@pytest.mark.unit
def test_add_manual_proxy():
    client = WeiboClient()
    client.add_proxy("http://1.2.3.4:8080", ttl=600)
    assert client.get_proxy_pool_size() == 1
```

