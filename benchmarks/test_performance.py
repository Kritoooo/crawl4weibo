"""
Performance and stress testing for crawl4weibo client.

This module provides realistic performance testing that simulates actual crawling workflow:
- Search posts by topic/keyword
- Extract post BIDs from search results
- Crawl detailed content for each post
- Measure posts per second throughput
- Support concurrent crawling with multiple workers
"""

import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import pytest

from crawl4weibo.core.client import WeiboClient
from crawl4weibo.models.post import Post


@dataclass
class ErrorDetail:
    """Error detail record."""
    bid: str = ""
    error_type: str = ""
    error_message: str = ""
    timestamp: float = 0.0


@dataclass
class CrawlMetrics:
    """Crawling performance metrics."""
    # Search phase metrics
    search_requests: int = 0
    search_successful: int = 0
    search_failed: int = 0
    search_time: float = 0.0
    posts_found: int = 0  # Total BIDs found from search

    # Detail crawling metrics
    detail_requests: int = 0
    detail_successful: int = 0
    detail_failed: int = 0
    detail_time: float = 0.0
    posts_crawled: int = 0  # Successfully crawled detailed posts

    # Overall metrics
    total_time: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

    # Response times
    search_response_times: List[float] = field(default_factory=list)
    detail_response_times: List[float] = field(default_factory=list)

    # Errors - now with detailed information
    search_errors: List[ErrorDetail] = field(default_factory=list)
    detail_errors: List[ErrorDetail] = field(default_factory=list)

    # Crawled data
    crawled_bids: Set[str] = field(default_factory=set)
    failed_bids: Set[str] = field(default_factory=set)

    @property
    def search_success_rate(self) -> float:
        """Search success rate."""
        if self.search_requests == 0:
            return 0.0
        return (self.search_successful / self.search_requests) * 100

    @property
    def detail_success_rate(self) -> float:
        """Detail crawling success rate."""
        if self.detail_requests == 0:
            return 0.0
        return (self.detail_successful / self.detail_requests) * 100

    @property
    def overall_success_rate(self) -> float:
        """Overall success rate."""
        total = self.search_requests + self.detail_requests
        successful = self.search_successful + self.detail_successful
        if total == 0:
            return 0.0
        return (successful / total) * 100

    @property
    def posts_per_second(self) -> float:
        """Calculate posts crawled per second (main metric)."""
        if self.total_time == 0:
            return 0.0
        return self.posts_crawled / self.total_time

    @property
    def avg_search_time(self) -> float:
        """Average search response time."""
        if not self.search_response_times:
            return 0.0
        return statistics.mean(self.search_response_times)

    @property
    def avg_detail_time(self) -> float:
        """Average detail crawling response time."""
        if not self.detail_response_times:
            return 0.0
        return statistics.mean(self.detail_response_times)

    def print_summary(self, test_name: str = "Crawling Performance Test"):
        """Print formatted test summary."""
        print(f"\n{'=' * 80}")
        print(f"{test_name:^80}")
        print(f"{'=' * 80}")

        # Main performance metric
        print(f"\n🎯 PRIMARY METRIC")
        print(f"Posts Crawled/Second:     {self.posts_per_second:.3f} posts/s")
        print(f"Total Posts Crawled:      {self.posts_crawled}")
        print(f"Actual Elapsed Time:      {self.total_time:.2f}s")

        # Calculate concurrency speedup if applicable
        if self.detail_time > 0 and self.total_time > 0:
            speedup = self.detail_time / self.total_time
            if speedup > 1.5:  # Only show if there's meaningful speedup
                print(f"Concurrency Speedup:      {speedup:.2f}x")

        # Search phase
        print(f"\n📊 SEARCH PHASE")
        print(f"Search Requests:          {self.search_requests}")
        print(f"  Successful:             {self.search_successful}")
        print(f"  Failed:                 {self.search_failed}")
        print(f"  Success Rate:           {self.search_success_rate:.2f}%")
        print(f"Posts Found (BIDs):       {self.posts_found}")
        print(f"Avg Search Time:          {self.avg_search_time:.2f}s")
        print(f"Sum of Search Times:      {self.search_time:.2f}s (all requests added)")

        # Detail crawling phase
        print(f"\n📝 DETAIL CRAWLING PHASE")
        print(f"Detail Requests:          {self.detail_requests}")
        print(f"  Successful:             {self.detail_successful}")
        print(f"  Failed:                 {self.detail_failed}")
        print(f"  Success Rate:           {self.detail_success_rate:.2f}%")
        print(f"Avg Detail Time:          {self.avg_detail_time:.2f}s")
        print(f"Sum of Detail Times:      {self.detail_time:.2f}s (all requests added)")

        # Overall statistics
        print(f"\n📈 OVERALL STATISTICS")
        total_requests = self.search_requests + self.detail_requests
        print(f"Total Requests:           {total_requests}")
        print(f"Overall Success Rate:     {self.overall_success_rate:.2f}%")
        print(f"Unique Posts Crawled:     {len(self.crawled_bids)}")
        print(f"Failed Posts:             {len(self.failed_bids)}")

        # Response time details
        if self.detail_response_times:
            print(f"\n⏱️  DETAIL RESPONSE TIME PERCENTILES")
            try:
                times_sorted = sorted(self.detail_response_times)
                p50 = statistics.median(times_sorted)
                p95 = statistics.quantiles(times_sorted, n=20)[18] if len(times_sorted) >= 20 else max(times_sorted)
                p99 = statistics.quantiles(times_sorted, n=100)[98] if len(times_sorted) >= 100 else max(times_sorted)
                print(f"  Min:                    {min(times_sorted):.2f}s")
                print(f"  P50 (Median):           {p50:.2f}s")
                print(f"  P95:                    {p95:.2f}s")
                print(f"  P99:                    {p99:.2f}s")
                print(f"  Max:                    {max(times_sorted):.2f}s")
            except (statistics.StatisticsError, ValueError):
                pass

        # Error summary
        all_errors = self.search_errors + self.detail_errors
        if all_errors:
            print(f"\n❌ ERROR SUMMARY")

            # Group by error type
            error_type_counts = {}
            error_details_by_type = {}
            for error in all_errors:
                error_type = error.error_type
                error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
                if error_type not in error_details_by_type:
                    error_details_by_type[error_type] = []
                error_details_by_type[error_type].append(error)

            # Print summary
            for error_type, count in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"\n  {error_type}: {count} occurrences")
                # Show first 3 examples
                examples = error_details_by_type[error_type][:3]
                for i, err in enumerate(examples, 1):
                    bid_info = f"BID: {err.bid}" if err.bid else "Search error"
                    print(f"    Example {i}: {bid_info}")
                    print(f"              Message: {err.error_message[:100]}")
                if len(error_details_by_type[error_type]) > 3:
                    print(f"    ... and {len(error_details_by_type[error_type]) - 3} more")

            # Suggest exporting detailed log
            print(f"\n  💡 Tip: Call metrics.export_error_log('filename.txt') to export full error details")

        print(f"{'=' * 80}\n")

    def export_error_log(self, filename: str = "error_log.txt"):
        """Export detailed error log to file for debugging."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("CRAWL4WEIBO PERFORMANCE TEST ERROR LOG\n")
            f.write("=" * 80 + "\n\n")

            # Search errors
            if self.search_errors:
                f.write("SEARCH ERRORS:\n")
                f.write("-" * 80 + "\n")
                for i, err in enumerate(self.search_errors, 1):
                    f.write(f"\nError #{i}:\n")
                    f.write(f"  Type: {err.error_type}\n")
                    f.write(f"  Time: {err.timestamp}\n")
                    f.write(f"  Message: {err.error_message}\n")
                f.write("\n")

            # Detail crawling errors
            if self.detail_errors:
                f.write("DETAIL CRAWLING ERRORS:\n")
                f.write("-" * 80 + "\n")
                for i, err in enumerate(self.detail_errors, 1):
                    f.write(f"\nError #{i}:\n")
                    f.write(f"  BID: {err.bid}\n")
                    f.write(f"  Type: {err.error_type}\n")
                    f.write(f"  Time: {err.timestamp}\n")
                    f.write(f"  Message: {err.error_message}\n")
                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write(f"Total Errors: {len(self.search_errors) + len(self.detail_errors)}\n")
            f.write("=" * 80 + "\n")

        print(f"Error log exported to: {filename}")


class TopicCrawler:
    """
    Realistic topic-based post crawler for performance testing.

    This crawler simulates real-world crawling workflow:
    1. Search posts by topic/keyword
    2. Extract BIDs from search results
    3. Crawl detailed content for each post
    4. Measure throughput (posts per second)
    """

    def __init__(self, cookies: str = None, proxy_api_url: str = None, use_once_proxy: bool = False):
        """
        Initialize topic crawler.

        Args:
            cookies: Weibo cookies for authentication
            proxy_api_url: Optional proxy API URL for testing with proxies
        """
        self.cookies = cookies
        self.proxy_api_url = proxy_api_url
        self.use_once_proxy = use_once_proxy
        self.lock = threading.Lock()

    def _create_client(self) -> WeiboClient:
        """Create a new WeiboClient instance."""
        return WeiboClient(
            cookies=self.cookies,
            proxy_api_url=self.proxy_api_url,
            use_once_proxy=self.use_once_proxy,
            log_level="WARNING"  # Reduce log noise during testing
        )

    def _search_posts(
        self,
        client: WeiboClient,
        query: str,
        page: int,
        metrics: CrawlMetrics
    ) -> List[str]:
        """
        Search posts and extract BIDs.

        Args:
            client: WeiboClient instance
            query: Search query
            page: Page number
            metrics: Metrics object to update

        Returns:
            List of BIDs found
        """
        start_time = time.time()
        bids = []

        try:
            posts = client.search_posts(query=query, page=page)
            bids = [post.bid for post in posts if post.bid]

            with self.lock:
                metrics.search_successful += 1
                metrics.posts_found += len(bids)

        except Exception as e:
            error_detail = ErrorDetail(
                bid="",
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=time.time()
            )
            with self.lock:
                metrics.search_failed += 1
                metrics.search_errors.append(error_detail)

        finally:
            end_time = time.time()
            elapsed = end_time - start_time
            with self.lock:
                metrics.search_requests += 1
                metrics.search_response_times.append(elapsed)
                metrics.search_time += elapsed

        return bids

    def _crawl_post_detail(
        self,
        client: WeiboClient,
        bid: str,
        metrics: CrawlMetrics
    ) -> Optional[Post]:
        """
        Crawl post detail by BID.

        Args:
            client: WeiboClient instance
            bid: Post BID
            metrics: Metrics object to update

        Returns:
            Post object or None on error
        """
        start_time = time.time()
        post = None

        try:
            post = client.get_post_by_bid(bid=bid)

            with self.lock:
                metrics.detail_successful += 1
                metrics.posts_crawled += 1
                metrics.crawled_bids.add(bid)

        except Exception as e:
            error_detail = ErrorDetail(
                bid=bid,
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=time.time()
            )
            with self.lock:
                metrics.detail_failed += 1
                metrics.detail_errors.append(error_detail)
                metrics.failed_bids.add(bid)

        finally:
            end_time = time.time()
            elapsed = end_time - start_time
            with self.lock:
                metrics.detail_requests += 1
                metrics.detail_response_times.append(elapsed)
                metrics.detail_time += elapsed

        return post

    def crawl_topic_sequential(
        self,
        query: str,
        search_pages: int = 1,
        max_posts: int = None
    ) -> CrawlMetrics:
        """
        Sequentially crawl posts from a topic (single-threaded).

        Workflow:
        1. Search for posts by query (multiple pages if specified)
        2. Extract BIDs from search results
        3. Crawl details for each BID sequentially

        Args:
            query: Search query/topic
            search_pages: Number of search pages to crawl
            max_posts: Maximum number of posts to crawl (None = unlimited)

        Returns:
            CrawlMetrics with performance data
        """
        metrics = CrawlMetrics()
        client = self._create_client()
        all_bids = []

        print(f"\n{'=' * 80}")
        print(f"Sequential Topic Crawl: '{query}'")
        print(f"Search Pages: {search_pages}, Max Posts: {max_posts or 'unlimited'}")
        print(f"{'=' * 80}\n")

        metrics.start_time = time.time()

        # Phase 1: Search and collect BIDs
        print(f"Phase 1: Searching for posts...")
        for page in range(1, search_pages + 1):
            print(f"  Searching page {page}/{search_pages}...")
            bids = self._search_posts(client, query, page, metrics)
            all_bids.extend(bids)
            print(f"    Found {len(bids)} posts on page {page}")

            if max_posts and len(all_bids) >= max_posts:
                all_bids = all_bids[:max_posts]
                break

        print(f"\nPhase 1 Complete: Found {len(all_bids)} total BIDs\n")

        # Phase 2: Crawl details for each BID
        print(f"Phase 2: Crawling post details...")
        for i, bid in enumerate(all_bids, 1):
            print(f"  Crawling post {i}/{len(all_bids)} (BID: {bid})...", end="\r")
            self._crawl_post_detail(client, bid, metrics)

        print(f"\nPhase 2 Complete: Crawled {metrics.posts_crawled} posts\n")

        metrics.end_time = time.time()
        metrics.total_time = metrics.end_time - metrics.start_time

        return metrics

    def crawl_topic_concurrent(
        self,
        query: str,
        search_pages: int = 1,
        max_posts: int = None,
        num_workers: int = 5
    ) -> CrawlMetrics:
        """
        Concurrently crawl posts from a topic (multi-threaded).

        Workflow:
        1. Search for posts by query (single-threaded)
        2. Extract BIDs from search results
        3. Crawl details for each BID concurrently using thread pool
           Each worker maintains its own client for the entire session

        Args:
            query: Search query/topic
            search_pages: Number of search pages to crawl
            max_posts: Maximum number of posts to crawl (None = unlimited)
            num_workers: Number of concurrent worker threads

        Returns:
            CrawlMetrics with performance data
        """
        metrics = CrawlMetrics()
        client = self._create_client()
        all_bids = []

        print(f"\n{'=' * 80}")
        print(f"Concurrent Topic Crawl: '{query}'")
        print(f"Search Pages: {search_pages}, Max Posts: {max_posts or 'unlimited'}, Workers: {num_workers}")
        print(f"{'=' * 80}\n")

        metrics.start_time = time.time()

        # Phase 1: Search and collect BIDs (sequential)
        print(f"Phase 1: Searching for posts...")
        for page in range(1, search_pages + 1):
            print(f"  Searching page {page}/{search_pages}...")
            bids = self._search_posts(client, query, page, metrics)
            all_bids.extend(bids)
            print(f"    Found {len(bids)} posts on page {page}")

            if max_posts and len(all_bids) >= max_posts:
                all_bids = all_bids[:max_posts]
                break

        print(f"\nPhase 1 Complete: Found {len(all_bids)} total BIDs\n")

        if not all_bids:
            print("No BIDs found. Skipping Phase 2.")
            metrics.end_time = time.time()
            metrics.total_time = metrics.end_time - metrics.start_time
            return metrics

        # Phase 2: Crawl details concurrently
        # Each worker gets its own client and a list of BIDs to process
        print(f"Phase 2: Crawling post details (concurrent with {num_workers} workers)...")

        # Distribute BIDs among workers
        from queue import Queue
        bid_queue = Queue()
        for bid in all_bids:
            bid_queue.put(bid)

        completed_count = [0]  # Use list to allow modification in nested function

        def worker_task(worker_id: int):
            """Worker function - maintains one client for all its requests."""
            worker_client = self._create_client()
            local_count = 0

            while not bid_queue.empty():
                try:
                    bid = bid_queue.get_nowait()
                except:
                    break

                try:
                    self._crawl_post_detail(worker_client, bid, metrics)
                    local_count += 1

                    with self.lock:
                        completed_count[0] += 1
                        print(f"  Progress: {completed_count[0]}/{len(all_bids)} posts crawled "
                              f"(Worker-{worker_id}: {local_count})", end="\r")

                except Exception as e:
                    print(f"\n  Worker-{worker_id} error on {bid}: {e}")

                finally:
                    bid_queue.task_done()

        # Start workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_workers)]

            # Wait for all workers to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"\n  Worker thread failed: {e}")

        print(f"\nPhase 2 Complete: Crawled {metrics.posts_crawled} posts\n")

        metrics.end_time = time.time()
        metrics.total_time = metrics.end_time - metrics.start_time

        return metrics

    def crawl_topic_timed(
        self,
        query: str,
        duration_seconds: int,
        num_workers: int = 1,
        search_pages: int = 5
    ) -> CrawlMetrics:
        """
        Crawl posts for a fixed time duration.

        Useful for measuring sustained throughput over time.

        Args:
            query: Search query/topic
            duration_seconds: How long to run the test
            num_workers: Number of concurrent workers
            search_pages: Number of search pages to collect BIDs from

        Returns:
            CrawlMetrics with performance data
        """
        metrics = CrawlMetrics()
        client = self._create_client()

        print(f"\n{'=' * 80}")
        print(f"Timed Topic Crawl: '{query}'")
        print(f"Duration: {duration_seconds}s, Workers: {num_workers}")
        print(f"{'=' * 80}\n")

        metrics.start_time = time.time()
        end_time = metrics.start_time + duration_seconds

        # Phase 1: Collect BID pool
        print(f"Phase 1: Building BID pool from {search_pages} pages...")
        bid_pool = []
        for page in range(1, search_pages + 1):
            bids = self._search_posts(client, query, page, metrics)
            bid_pool.extend(bids)
            print(f"  Page {page}: Found {len(bids)} BIDs (total: {len(bid_pool)})")

        print(f"\nPhase 1 Complete: Collected {len(bid_pool)} BIDs\n")

        if not bid_pool:
            print("No BIDs found. Aborting test.")
            metrics.end_time = time.time()
            metrics.total_time = metrics.end_time - metrics.start_time
            return metrics

        # Phase 2: Crawl continuously until time expires
        print(f"Phase 2: Crawling for {duration_seconds} seconds...\n")

        bid_index = [0]  # Use list to share among threads
        stop_flag = threading.Event()

        def worker_task(worker_id: int):
            """Worker function that crawls continuously - maintains one client."""
            worker_client = self._create_client()
            local_count = 0

            while not stop_flag.is_set():
                if time.time() >= end_time:
                    stop_flag.set()
                    break

                # Get next BID (round-robin)
                with self.lock:
                    if bid_index[0] >= len(bid_pool):
                        bid_index[0] = 0
                    bid = bid_pool[bid_index[0]]
                    bid_index[0] += 1

                try:
                    self._crawl_post_detail(worker_client, bid, metrics)
                    local_count += 1
                except Exception as e:
                    # Errors are already logged in _crawl_post_detail
                    pass

        # Start workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_workers)]

            # Monitor progress
            while time.time() < end_time:
                elapsed = time.time() - metrics.start_time
                current_rate = metrics.posts_crawled / elapsed if elapsed > 0 else 0
                print(f"  Time: {elapsed:.1f}s | Posts: {metrics.posts_crawled} | Rate: {current_rate:.3f} posts/s", end="\r")
                time.sleep(1)

            stop_flag.set()

            # Wait for all workers to finish
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"\n  Worker thread failed: {e}")

        print(f"\nPhase 2 Complete: Crawled {metrics.posts_crawled} posts in {duration_seconds}s\n")

        metrics.end_time = time.time()
        metrics.total_time = metrics.end_time - metrics.start_time

        return metrics

    def compare_proxy_performance(
        self,
        query: str,
        search_pages: int = 1,
        max_posts: int = 20
    ) -> Dict[str, CrawlMetrics]:
        """
        Compare performance with and without proxy.

        Args:
            query: Search query/topic
            search_pages: Number of search pages
            max_posts: Maximum posts to crawl per test

        Returns:
            Dictionary with 'no_proxy' and 'with_proxy' metrics
        """
        results = {}

        # Test without proxy
        print("\n" + "=" * 80)
        print("Testing WITHOUT proxy...")
        print("=" * 80)
        original_proxy = self.proxy_api_url
        self.proxy_api_url = None
        results['no_proxy'] = self.crawl_topic_sequential(query, search_pages, max_posts)
        results['no_proxy'].print_summary("Performance Test - No Proxy")

        # Test with proxy
        if original_proxy:
            print("\n" + "=" * 80)
            print("Testing WITH proxy...")
            print("=" * 80)
            self.proxy_api_url = original_proxy
            results['with_proxy'] = self.crawl_topic_sequential(query, search_pages, max_posts)
            results['with_proxy'].print_summary("Performance Test - With Proxy")

            # Print comparison
            print("\n" + "=" * 80)
            print("PROXY PERFORMANCE COMPARISON")
            print("=" * 80)
            print(f"{'Metric':<30} {'No Proxy':<20} {'With Proxy':<20}")
            print("-" * 80)
            print(f"{'Posts/Second':<30} {results['no_proxy'].posts_per_second:<20.3f} {results['with_proxy'].posts_per_second:<20.3f}")
            print(f"{'Success Rate':<30} {results['no_proxy'].overall_success_rate:<20.2f}% {results['with_proxy'].overall_success_rate:<20.2f}%")
            print(f"{'Avg Detail Time':<30} {results['no_proxy'].avg_detail_time:<20.2f}s {results['with_proxy'].avg_detail_time:<20.2f}s")
            print(f"{'Total Time':<30} {results['no_proxy'].total_time:<20.2f}s {results['with_proxy'].total_time:<20.2f}s")
            print("=" * 80 + "\n")

        return results


# ==================== PYTEST TEST CASES ====================

@pytest.mark.integration
def test_sequential_topic_crawl():
    """Test sequential topic-based crawling."""
    cookies = getattr(pytest, 'cookies', None)
    crawler = TopicCrawler(cookies=cookies)

    metrics = crawler.crawl_topic_sequential(
        query="Python编程",
        search_pages=2,
        max_posts=10
    )

    metrics.print_summary("Sequential Topic Crawl Test")

    # Assertions
    assert metrics.search_requests > 0
    assert metrics.posts_found > 0
    assert metrics.posts_per_second > 0


@pytest.mark.integration
def test_concurrent_topic_crawl():
    """Test concurrent topic-based crawling."""
    cookies = getattr(pytest, 'cookies', None)
    crawler = TopicCrawler(cookies=cookies)

    metrics = crawler.crawl_topic_concurrent(
        query="人工智能",
        search_pages=2,
        max_posts=20,
        num_workers=5
    )

    metrics.print_summary("Concurrent Topic Crawl Test")

    # Assertions
    assert metrics.search_requests > 0
    assert metrics.posts_found > 0
    assert metrics.posts_per_second > 0


@pytest.mark.integration
def test_timed_crawl():
    """Test timed crawling (fixed duration)."""
    cookies = getattr(pytest, 'cookies', None)
    crawler = TopicCrawler(cookies=cookies)

    metrics = crawler.crawl_topic_timed(
        query="科技",
        duration_seconds=30,
        num_workers=3
    )

    metrics.print_summary("Timed Crawl Test (30 seconds)")

    # Assertions
    assert metrics.total_time >= 30
    assert metrics.posts_crawled > 0


@pytest.mark.integration
def test_proxy_comparison():
    """Test proxy performance comparison."""
    cookies = getattr(pytest, 'cookies', None)
    proxy_api_url = getattr(pytest, 'proxy_api_url', None)

    if not proxy_api_url:
        pytest.skip("Proxy API URL not configured")

    crawler = TopicCrawler(cookies=cookies, proxy_api_url=proxy_api_url)

    results = crawler.compare_proxy_performance(
        query="微博",
        search_pages=1,
        max_posts=10
    )

    # Assertions
    assert 'no_proxy' in results
    assert 'with_proxy' in results
    assert results['no_proxy'].posts_crawled > 0
    assert results['with_proxy'].posts_crawled > 0


# ==================== STANDALONE EXECUTION ====================

if __name__ == "__main__":
    """
    Standalone execution for manual performance testing.

    Usage:
        python test_performance.py
    """
    print("=" * 80)
    print("crawl4weibo Topic Crawling Performance Test")
    print("=" * 80)

    # Configuration
    cookies_input = input("\nEnter cookies (press Enter to skip): ").strip()
    cookies = cookies_input if cookies_input else None

    proxy_input = input("Enter proxy API URL (press Enter to skip): ").strip()
    proxy_api_url = proxy_input if proxy_input else None

    use_once_proxy_input = input("Use one-time proxy mode? (y/n, default: n): ").strip().lower()
    use_once_proxy = use_once_proxy_input == 'y'

    query = input("Enter search query (default: 'Python'): ").strip() or "Python"

    crawler = TopicCrawler(cookies=cookies, proxy_api_url=proxy_api_url, use_once_proxy=use_once_proxy)

    # Test menu
    print("\nSelect test type:")
    print("1. Sequential crawl (single-threaded)")
    print("2. Concurrent crawl (multi-threaded)")
    print("3. Timed crawl (fixed duration)")
    print("4. Proxy comparison")

    choice = input("\nEnter choice (1-4, default: 1): ").strip() or "1"

    if choice == "1":
        pages = int(input("Search pages (default: 2): ").strip() or "2")
        max_posts = input("Max posts (default: 20): ").strip()
        max_posts = int(max_posts) if max_posts else 20

        metrics = crawler.crawl_topic_sequential(query, pages, max_posts)
        metrics.print_summary("Sequential Crawl Test")

    elif choice == "2":
        pages = int(input("Search pages (default: 2): ").strip() or "2")
        max_posts = input("Max posts (default: 30): ").strip()
        max_posts = int(max_posts) if max_posts else 30
        workers = int(input("Concurrent workers (default: 5): ").strip() or "5")

        metrics = crawler.crawl_topic_concurrent(query, pages, max_posts, workers)
        metrics.print_summary("Concurrent Crawl Test")

    elif choice == "3":
        duration = int(input("Duration in seconds (default: 60): ").strip() or "60")
        workers = int(input("Concurrent workers (default: 3): ").strip() or "3")

        metrics = crawler.crawl_topic_timed(query, duration, workers)
        metrics.print_summary("Timed Crawl Test")

    elif choice == "4":
        if not proxy_api_url:
            print("\nError: Proxy API URL required for comparison test")
        else:
            pages = int(input("Search pages (default: 1): ").strip() or "1")
            max_posts = int(input("Max posts (default: 10): ").strip() or "10")

            crawler.compare_proxy_performance(query, pages, max_posts)

    else:
        print("Invalid choice")

    print("\nTest completed!")
