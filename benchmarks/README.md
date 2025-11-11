# Benchmarks

This directory contains performance and stress testing tools for crawl4weibo.

## Contents

- `test_performance.py` - Performance and stress test suite with realistic crawling scenarios
- `docs/` - Testing documentation and guides
  - `PERFORMANCE_TESTING_GUIDE.md` - Comprehensive testing methodology and metrics
  - `PERFORMANCE_TEST_IMPROVEMENTS.md` - Test implementation improvements and design decisions
  - `STRESS_TESTING_GUIDE.md` - Stress testing guide (Chinese)

## Running Tests

### Interactive Mode (Recommended)

```bash
cd benchmarks
python test_performance.py
```

Follow the prompts to configure:
- Cookies (optional)
- Proxy API URL (optional)
- Search keyword (e.g., "Python")
- Test type (1-4)

### Using pytest

```bash
# Run all performance tests
pytest benchmarks/test_performance.py -v -m integration

# Run specific tests
pytest benchmarks/test_performance.py::test_sequential_topic_crawl -v
pytest benchmarks/test_performance.py::test_concurrent_topic_crawl -v
pytest benchmarks/test_performance.py::test_timed_crawl -v
pytest benchmarks/test_performance.py::test_proxy_comparison -v
```

### Programmatic Usage

```python
from benchmarks.test_performance import TopicCrawler

# Configure test
crawler = TopicCrawler(
    cookies=None,  # Optional
    proxy_api_url=None,  # Optional
    query="Python"
)

# Run sequential crawl
metrics = crawler.crawl_topic_sequential(post_count=10)
crawler.print_metrics(metrics)

# Run concurrent crawl
metrics = crawler.crawl_topic_concurrent(post_count=20, max_workers=5)
crawler.print_metrics(metrics)
```

## Test Scenarios

1. **Sequential Crawling** - Basic single-threaded crawling
2. **Concurrent Crawling** - Multi-threaded crawling with thread pool
3. **Timed Crawling** - Time-limited crawling session
4. **Proxy Comparison** - Compare crawling with and without proxies

## Documentation

For detailed information on:
- Performance metrics and baselines
- Test design methodology
- Stress testing strategies
- Expected throughput and latency

See the guides in the `docs/` directory.
