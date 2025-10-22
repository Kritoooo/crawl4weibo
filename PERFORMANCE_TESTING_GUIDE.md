# Crawl4Weibo Performance Testing Guide

## Overview

The crawl4weibo library is a **synchronous, single-threaded HTTP crawler** with built-in rate limiting. This guide explains how to design performance tests for measuring throughput, latency, and scalability.

## Key Characteristics for Testing

### Synchronous Design
- Each HTTP request blocks until completion
- No concurrent requests within a single client
- Sequential operation: Request → Wait for response → Process → Delay → Next request

### Built-in Rate Limiting (Hardcoded)
```
get_user_posts():      1-3 sec delay before request
search_users():        1-3 sec delay before request
search_posts():        1-3 sec delay before request
image downloads:       1-3 sec delay between images
pagination:            2-4 sec delay between pages
432 error retry:       4-7 sec backoff
network error retry:   2-5 sec backoff
```

### Fixed Constraints
- Request timeout: 5 seconds (hardcoded)
- Max retries: 3 attempts (hardcoded in _request())
- No dynamic delay adjustment possible
- No concurrency built-in (requires external threading)

---

## Performance Metrics to Measure

### 1. Throughput
- **Requests per second** (RPS) for single client
- **Concurrent throughput** with multiple clients
- **Operations per minute** (accounting for built-in delays)

### 2. Latency
- **Mean response time** (HTTP request only)
- **Total operation time** (including built-in delays)
- **95th/99th percentile latency**
- **Timeout rate** (% of requests exceeding 5 sec)

### 3. Reliability
- **Success rate** (% of requests succeeding)
- **Error rate breakdown** (4xx, 5xx, timeouts, 432 blocks)
- **Retry effectiveness** (success after retry vs. final failure)

### 4. Resource Utilization
- **Memory per client** (requests.Session overhead)
- **CPU usage** (JSON parsing, disk I/O for downloads)
- **Network bandwidth** (bytes transferred)

### 5. Proxy Effectiveness
- **Proxy pool hit rate** (% of requests using proxy)
- **Proxy failure rate** (% of proxy requests failing)
- **Pool rotation time** (average time between using same proxy)

---

## Test Scenario 1: Single Client Baseline

**Purpose**: Establish baseline performance with 1 client

**Duration**: 10 minutes

**Operations**:
```python
from crawl4weibo import WeiboClient
import time

def single_client_test():
    client = WeiboClient()
    
    test_uid = "2656274875"
    test_query = "人工智能"
    
    results = {
        "total_requests": 0,
        "total_time": 0,
        "by_operation": {}
    }
    
    start_time = time.time()
    
    # Operation 1: Get user (no built-in delay)
    t = time.time()
    user = client.get_user_by_uid(test_uid)
    results["by_operation"]["get_user"] = time.time() - t
    results["total_requests"] += 1
    
    # Operation 2: Get user posts (1-3 sec delay built-in)
    t = time.time()
    posts = client.get_user_posts(test_uid, page=1)
    results["by_operation"]["get_posts"] = time.time() - t
    results["total_requests"] += 1
    
    # Operation 3: Search posts (1-3 sec delay built-in)
    t = time.time()
    search_results = client.search_posts(test_query, page=1)
    results["by_operation"]["search_posts"] = time.time() - t
    results["total_requests"] += 1
    
    # Operation 4: Get single post (no built-in delay)
    if posts:
        t = time.time()
        post = client.get_post_by_bid(posts[0].bid)
        results["by_operation"]["get_post_by_bid"] = time.time() - t
        results["total_requests"] += 1
    
    results["total_time"] = time.time() - start_time
    
    return results
```

**Expected Metrics**:
- Total time per cycle: ~12-15 seconds (including built-in delays)
- Operations per cycle: 4
- Throughput: ~0.27 ops/sec
- Mean latency per operation: ~3-4 seconds

---

## Test Scenario 2: Multi-Client Concurrent Load

**Purpose**: Measure throughput with parallel clients

**Duration**: 5 minutes

**Implementation**:
```python
from concurrent.futures import ThreadPoolExecutor
import time
from crawl4weibo import WeiboClient

def multi_client_test(num_clients=5, operations_per_client=10):
    """
    Test multiple clients making concurrent requests
    
    Args:
        num_clients: Number of parallel threads/clients
        operations_per_client: Operations per client
    """
    
    def client_worker(client_id):
        client = WeiboClient()
        results = {
            "client_id": client_id,
            "operations": 0,
            "errors": 0,
            "timings": []
        }
        
        for i in range(operations_per_client):
            try:
                t = time.time()
                user = client.get_user_by_uid("2656274875")
                elapsed = time.time() - t
                results["timings"].append(elapsed)
                results["operations"] += 1
            except Exception as e:
                results["errors"] += 1
        
        return results
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_clients) as executor:
        futures = [
            executor.submit(client_worker, i) 
            for i in range(num_clients)
        ]
        results = [f.result() for f in futures]
    
    total_time = time.time() - start_time
    
    # Calculate metrics
    total_ops = sum(r["operations"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    all_timings = []
    for r in results:
        all_timings.extend(r["timings"])
    
    all_timings.sort()
    
    metrics = {
        "total_time_sec": total_time,
        "total_operations": total_ops,
        "total_errors": total_errors,
        "throughput_ops_per_sec": total_ops / total_time,
        "mean_latency_sec": sum(all_timings) / len(all_timings),
        "p95_latency_sec": all_timings[int(len(all_timings) * 0.95)],
        "p99_latency_sec": all_timings[int(len(all_timings) * 0.99)],
        "success_rate": total_ops / (total_ops + total_errors) if (total_ops + total_errors) > 0 else 0
    }
    
    return metrics
```

**Expected Results** (5 clients, 10 ops each):
- Total requests: 50
- Total time: ~5-10 minutes (due to built-in delays)
- Throughput: ~0.08-0.17 ops/sec across all clients
- Mean latency: ~3-4 seconds per request
- Success rate: 95%+ (depending on API availability)

---

## Test Scenario 3: Rate Limit & Error Recovery

**Purpose**: Measure behavior under 432 anti-crawler blocks

**Duration**: Until 432 error occurs (10-30 minutes)

**Implementation**:
```python
def error_recovery_test():
    """
    Test how client handles 432 anti-crawler blocks and network errors
    """
    client = WeiboClient()
    
    results = {
        "total_requests": 0,
        "successful": 0,
        "error_432": 0,
        "error_network": 0,
        "error_parse": 0,
        "retry_count": [],
        "recovery_times": []
    }
    
    from crawl4weibo.exceptions.base import NetworkError, ParseError
    
    for i in range(100):  # Try 100 requests
        try:
            t = time.time()
            # This will eventually trigger 432
            posts = client.get_user_posts("2656274875", page=i % 10 + 1)
            results["successful"] += 1
            results["total_requests"] += 1
        except NetworkError as e:
            if "432" in str(e):
                results["error_432"] += 1
            else:
                results["error_network"] += 1
            results["total_requests"] += 1
            results["recovery_times"].append(time.time() - t)
        except ParseError as e:
            results["error_parse"] += 1
            results["total_requests"] += 1
        except Exception as e:
            results["total_requests"] += 1
    
    results["success_rate"] = results["successful"] / results["total_requests"]
    results["error_rate_432"] = results["error_432"] / results["total_requests"]
    
    return results
```

**Expected Results**:
- Success rate: 90-95% initially
- 432 error: ~0-5% after sustained requests
- Recovery time: 4-7 seconds per 432 retry
- Mean backoff delay: ~5-6 seconds

---

## Test Scenario 4: Proxy Pool Performance

**Purpose**: Measure proxy rotation and effectiveness

**Implementation**:
```python
def proxy_pool_test(use_dynamic=False):
    """
    Test proxy pool performance
    
    Args:
        use_dynamic: Use dynamic API or manual proxies
    """
    
    if use_dynamic:
        client = WeiboClient(
            proxy_api_url="http://api.proxy.com/get?format=json",
            proxy_pool_size=5,
            proxy_fetch_strategy="random"
        )
    else:
        client = WeiboClient()
        # Add static proxies
        for i in range(5):
            client.add_proxy(f"http://proxy{i}.example.com:8080", ttl=600)
    
    results = {
        "requests_with_proxy": 0,
        "requests_without_proxy": 0,
        "proxy_pool_sizes": [],
        "proxy_rotations": {},
        "success_with_proxy": 0,
        "success_without_proxy": 0
    }
    
    for i in range(50):
        pool_size = client.get_proxy_pool_size()
        results["proxy_pool_sizes"].append(pool_size)
        
        try:
            if use_dynamic:
                # Force proxy usage
                user = client.get_user_by_uid("2656274875", use_proxy=True)
                results["requests_with_proxy"] += 1
                results["success_with_proxy"] += 1
            else:
                # Use static proxies
                user = client.get_user_by_uid("2656274875", use_proxy=True)
                results["requests_with_proxy"] += 1
                results["success_with_proxy"] += 1
        except Exception as e:
            results["requests_with_proxy"] += 1
    
    results["mean_pool_size"] = sum(results["proxy_pool_sizes"]) / len(results["proxy_pool_sizes"])
    results["proxy_success_rate"] = results["success_with_proxy"] / results["requests_with_proxy"] if results["requests_with_proxy"] > 0 else 0
    
    return results
```

**Expected Results**:
- Proxy pool size: stable at configured size (default: 10)
- Success rate with proxy: 95%+
- Rotation: random or round-robin based on strategy

---

## Test Scenario 5: Image Download Performance

**Purpose**: Measure download throughput and batch efficiency

**Implementation**:
```python
def image_download_test():
    """
    Test image download performance
    """
    client = WeiboClient()
    
    results = {
        "total_images": 0,
        "successful_downloads": 0,
        "failed_downloads": 0,
        "duplicate_skips": 0,
        "total_bytes": 0,
        "time_per_image": [],
        "total_time": 0
    }
    
    start_time = time.time()
    
    # Fetch posts with images
    posts = client.get_user_posts("2656274875", page=1)
    
    # Download images
    for post in posts[:5]:  # Test with first 5 posts
        if post.pic_urls:
            t = time.time()
            download_results = client.download_post_images(post)
            elapsed = time.time() - t
            
            for url, filepath in download_results.items():
                results["total_images"] += 1
                if filepath:
                    results["successful_downloads"] += 1
                    results["time_per_image"].append(elapsed / len(download_results))
                else:
                    results["failed_downloads"] += 1
    
    results["total_time"] = time.time() - start_time
    results["mean_time_per_image"] = sum(results["time_per_image"]) / len(results["time_per_image"]) if results["time_per_image"] else 0
    results["throughput_images_per_sec"] = results["successful_downloads"] / results["total_time"] if results["total_time"] > 0 else 0
    
    return results
```

**Expected Results**:
- Total images: 10-50 (depending on post content)
- Successful download rate: 90%+
- Mean time per image: 2-5 seconds (including delays)
- Throughput: 0.2-0.5 images/sec

---

## Performance Testing Checklist

### Setup
- [ ] Install crawl4weibo: `pip install crawl4weibo`
- [ ] Configure test environment
- [ ] Set up metrics collection (time, memory, CPU)
- [ ] Prepare test data (UIDs, queries)

### Single Client Tests
- [ ] Baseline latency (no load)
- [ ] Operation breakdown (time per operation type)
- [ ] Built-in delays validation
- [ ] Error handling (404, timeout, etc.)

### Multi-Client Tests
- [ ] 2 concurrent clients
- [ ] 5 concurrent clients
- [ ] 10 concurrent clients
- [ ] Measure throughput scaling

### Stress Tests
- [ ] Run until 432 error occurs
- [ ] Measure recovery time
- [ ] Measure resource usage over 1 hour
- [ ] Check memory leaks (memory growth trend)

### Proxy Tests
- [ ] Dynamic proxy pool behavior
- [ ] Static proxy rotation
- [ ] Proxy failure handling
- [ ] Pool size impact on performance

### Results Documentation
- [ ] Throughput (ops/sec) by scenario
- [ ] Latency percentiles (p50, p95, p99)
- [ ] Success/error rates
- [ ] Resource usage (memory, CPU, bandwidth)

---

## Tools for Performance Testing

### Simple Option: Manual Timing
```python
import time
import statistics

timings = []
for i in range(100):
    t = time.time()
    result = client.get_user_by_uid("2656274875")
    elapsed = time.time() - t
    timings.append(elapsed)

print(f"Mean: {statistics.mean(timings):.2f}s")
print(f"Median: {statistics.median(timings):.2f}s")
print(f"P99: {sorted(timings)[int(len(timings)*0.99)]:.2f}s")
```

### Better Option: Locust
```python
# Install: pip install locust
from locust import HttpUser, task, between
from crawl4weibo import WeiboClient

class WeiboUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.client = WeiboClient()
    
    @task
    def get_user(self):
        self.client.get_user_by_uid("2656274875")
    
    @task
    def search_posts(self):
        self.client.search_posts("人工智能")
```

### Best Option: Custom Framework
```python
# Use pytest-benchmark for micro-benchmarks
import pytest

@pytest.fixture
def client():
    return WeiboClient()

def test_get_user_performance(benchmark, client):
    result = benchmark(client.get_user_by_uid, "2656274875")
    assert result is not None
```

---

## Known Limitations for Testing

1. **Single-threaded client** - No built-in concurrency
   - Workaround: Use ThreadPoolExecutor for multiple clients

2. **Hardcoded delays** - Cannot adjust via configuration
   - Workaround: Fork library and modify delays for testing

3. **Fixed 5-second timeout** - Cannot increase/decrease
   - Impact: Long operations may timeout

4. **No async support** - Requires threading for parallelization
   - Workaround: Use concurrent.futures or asyncio wrapper

5. **Real API dependency** - Tests depend on Weibo API availability
   - Workaround: Use mocking (responses library) for unit tests

---

## Expected Performance Baselines

### Single Client (No Proxy)
- Throughput: 0.25 ops/sec
- Mean latency: 4 seconds per operation
- Success rate: 95%+

### 5 Concurrent Clients
- Throughput: 1.0-1.5 ops/sec (combined)
- Per-client latency: 4-6 seconds
- Success rate: 90%+

### With Proxies (5 in pool)
- Throughput: +10-20% improvement
- Error rate: -5-10% (fewer blocks)
- Pool rotation: Every 10-20 requests

### Image Downloads
- Success rate: 90%+
- Mean time per image: 2-5 seconds
- Throughput: 0.2-0.5 images/sec

---

## Reporting Results

### Key Metrics to Report
1. **Throughput** (operations per second)
2. **Latency** (mean, median, p95, p99)
3. **Success rate** (% of successful requests)
4. **Error breakdown** (% by error type)
5. **Resource usage** (memory, CPU, bandwidth)

### Visualization
- Line chart: Latency over time
- Histogram: Latency distribution
- Table: Success rates by operation type
- Box plot: Latency percentiles

### Recommendations
- Compare results across scenarios
- Identify bottlenecks
- Suggest proxy pool size
- Recommend concurrency limits

