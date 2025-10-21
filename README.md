# Crawl4Weibo

**[中文文档](README_zh.md)** | **English**

---

Crawl4Weibo is a ready-to-use Weibo (微博) web scraper Python library that simulates mobile requests, handles common anti-scraping strategies, and returns structured data models—ideal for data collection, analysis, and monitoring scenarios.

## ✨ Features
- **No Cookie Required**: Runs without cookies, automatically initializes session with mobile User-Agent
- **Built-in 432 Protection**: Handles anti-scraping protection with exponential backoff retry mechanism
- **Unified Proxy Pool Management**: Supports both dynamic and static IP proxy pools with configurable TTL, polling strategies, and automatic cleanup
- **Standardized Data Models**: Clean `User` and `Post` data models with recursive access to reposted content
- **Long Text Expansion**: Supports expanding truncated long posts, keyword search, user list fetching, and batch pagination
- **Image Download Utilities**: Download images from single posts, batches, or entire pages with duplicate file detection
- **Unified Logging & Error Types**: Quickly locate network, parsing, or authentication issues

## Installation
```bash
pip install crawl4weibo
```
Or use the faster `uv`:
```bash
uv pip install crawl4weibo
```

## Quick Start
```python
from crawl4weibo import WeiboClient

client = WeiboClient()
uid = "2656274875"

# Get user information
user = client.get_user_by_uid(uid)
print(f"{user.screen_name} - Followers: {user.followers_count}")

# Get user posts (with long text expansion)
posts = client.get_user_posts(uid, page=1, expand=True)
for post in posts[:3]:
    print(f"{post.text[:50]}... - Likes: {post.attitudes_count}")

# Search users
users = client.search_users("新浪")
for user in users[:3]:
    print(f"{user.screen_name} - Followers: {user.followers_count}")

# Search posts
results = client.search_posts("人工智能", page=1)
print(f"Found {len(results)} results")
```
For more examples, see [`examples/simple_example.py`](examples/simple_example.py).

**Run the example:**
```bash
# Clone the repository first
python examples/simple_example.py

# Or using uv
uv run python examples/simple_example.py
```

## Image Download Example
```python
from crawl4weibo import WeiboClient

client = WeiboClient()

# Method 1: Download images from a single post
post = client.get_post_by_bid("Q6FyDtbQc")
if post.pic_urls:
    results = client.download_post_images(
        post,
        download_dir="./downloads",
        subdir="single_post"
    )
    print(f"Successfully downloaded {sum(1 for p in results.values() if p)} images")

# Method 2: Batch download images from user posts
posts = client.get_user_posts("2656274875", page=1)
results = client.download_posts_images(
    posts[:3],  # Download images from first 3 posts
    download_dir="./downloads"
)

# Method 3: Download images from multiple pages of user posts
results = client.download_user_posts_images(
    uid="2656274875",
    pages=2,  # Download from first 2 pages
    download_dir="./downloads"
)
```
For more usage details, see [`examples/download_images_example.py`](examples/download_images_example.py).

**Run the example:**
```bash
python examples/download_images_example.py
```

## Proxy Pool Configuration Example
```python
from crawl4weibo import WeiboClient

# Method 1: Use dynamic proxy API
client = WeiboClient(
    proxy_api_url="http://api.proxy.com/get?format=json",
    dynamic_proxy_ttl=300,      # Dynamic proxy TTL in seconds
    proxy_pool_size=10,         # Proxy pool capacity
    proxy_fetch_strategy="random"  # random or round_robin
)

# Method 2: Manually add static proxies
client = WeiboClient()
client.add_proxy("http://1.2.3.4:8080", ttl=600)  # With TTL
client.add_proxy("http://5.6.7.8:8080")  # Never expires

# Method 3: Mix dynamic and static proxies
client = WeiboClient(
    proxy_api_url="http://api.proxy.com/get",
    proxy_pool_size=20
)
client.add_proxy("http://1.2.3.4:8080", ttl=None)

# Method 4: Custom parser (adapt to different proxy providers)
def custom_parser(data):
    return f"http://{data['result']['ip']}:{data['result']['port']}"

client = WeiboClient(
    proxy_api_url="http://custom-api.com/proxy",
    proxy_api_parser=custom_parser
)

# Flexible control of proxy usage per request
user = client.get_user_by_uid("2656274875", use_proxy=False)
posts = client.get_user_posts("2656274875", page=1)  # Uses proxy
```

## API Overview
- `get_user_by_uid(uid)`: Get user profile and statistics
- `get_user_posts(uid, page=1, expand=False)`: Fetch user timeline posts with optional long text expansion
- `get_post_by_bid(bid)`: Get full content and media info for a single post
- `search_users(query, page=1, count=10)` / `search_posts(query, page=1)`: Keyword search
- `download_post_images(post, ...)`, `download_user_posts_images(uid, pages=2, ...)`: Download image assets
- **Unified Exceptions**: `NetworkError`, `RateLimitError`, `UserNotFoundError`, etc., for business-level error handling

## Development & Testing
```bash
uv sync --dev                # Install dev dependencies
uv run pytest                # Run all tests (includes unit/integration/slow markers)
uv run ruff check crawl4weibo --fix
uv run ruff format crawl4weibo
uv run python examples/simple_example.py
```
For project structure, contribution guidelines, and more workflows, see `docs/DEVELOPMENT.md` and `AGENTS.md`.

## License
MIT License
