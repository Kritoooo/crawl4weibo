#!/usr/bin/env python

"""
Tests for rate limiting functionality
"""

import time
from unittest.mock import MagicMock

import pytest
import responses

from crawl4weibo.core.client import WeiboClient
from crawl4weibo.utils.rate_limit import RateLimitConfig, rate_limit


@pytest.mark.unit
class TestRateLimitConfig:
    """Test RateLimitConfig class"""

    def test_default_configuration(self):
        """Test default rate limit configuration"""
        config = RateLimitConfig()

        assert config.base_delay == (1.0, 3.0)
        assert config.min_delay == (0.1, 0.3)
        assert config.pool_size_threshold == 20
        assert config.disable_delay is False
        assert config.method_multipliers == {}

    def test_custom_configuration(self):
        """Test custom rate limit configuration"""
        config = RateLimitConfig(
            base_delay=(2.0, 4.0),
            min_delay=(0.05, 0.1),
            pool_size_threshold=50,
            method_multipliers={"search_posts": 0.5},
            disable_delay=True,
        )

        assert config.base_delay == (2.0, 4.0)
        assert config.min_delay == (0.05, 0.1)
        assert config.pool_size_threshold == 50
        assert config.method_multipliers == {"search_posts": 0.5}
        assert config.disable_delay is True

    def test_get_delay_disabled(self):
        """Test that delay is 0 when disabled"""
        config = RateLimitConfig(disable_delay=True)

        delay = config.get_delay("test_method", pool_size=10)
        assert delay == 0.0

    def test_get_delay_no_proxy(self):
        """Test delay calculation with no proxy pool"""
        config = RateLimitConfig(base_delay=(2.0, 4.0), min_delay=(0.1, 0.2))

        delay = config.get_delay("test_method", pool_size=0)

        # Should use base_delay when pool_size = 0
        assert 2.0 <= delay <= 4.0

    def test_get_delay_small_proxy_pool(self):
        """Test delay calculation with small proxy pool"""
        config = RateLimitConfig(
            base_delay=(2.0, 4.0), min_delay=(0.1, 0.2), pool_size_threshold=20
        )

        # With pool_size=10, ratio=0.5, so delay should be halfway between base and min
        delay = config.get_delay("test_method", pool_size=10)

        # Expected range: (2.0*0.5 + 0.1*0.5, 4.0*0.5 + 0.2*0.5) = (1.05, 2.1)
        assert 1.05 <= delay <= 2.1

    def test_get_delay_large_proxy_pool(self):
        """Test delay calculation with large proxy pool"""
        config = RateLimitConfig(
            base_delay=(2.0, 4.0), min_delay=(0.1, 0.2), pool_size_threshold=20
        )

        # With pool_size=100 (>= threshold), should use min_delay
        delay = config.get_delay("test_method", pool_size=100)

        assert 0.1 <= delay <= 0.2

    def test_get_delay_at_threshold(self):
        """Test delay calculation exactly at threshold"""
        config = RateLimitConfig(
            base_delay=(2.0, 4.0), min_delay=(0.1, 0.2), pool_size_threshold=20
        )

        delay = config.get_delay("test_method", pool_size=20)

        # At threshold, ratio=1.0, should use min_delay
        assert 0.1 <= delay <= 0.2

    def test_get_delay_with_method_multiplier(self):
        """Test delay calculation with method-specific multiplier"""
        config = RateLimitConfig(
            base_delay=(1.0, 2.0),
            min_delay=(0.1, 0.2),
            pool_size_threshold=20,
            method_multipliers={"fast_method": 0.5, "slow_method": 2.0},
        )

        # Test fast method (50% of normal delay)
        fast_delay = config.get_delay("fast_method", pool_size=0)
        assert 0.5 <= fast_delay <= 1.0  # 50% of base_delay

        # Test slow method (200% of normal delay)
        slow_delay = config.get_delay("slow_method", pool_size=0)
        assert 2.0 <= slow_delay <= 4.0  # 200% of base_delay

        # Test method without multiplier (uses 1.0)
        normal_delay = config.get_delay("normal_method", pool_size=0)
        assert 1.0 <= normal_delay <= 2.0

    def test_linear_interpolation(self):
        """Test that delay interpolation is linear"""
        config = RateLimitConfig(
            base_delay=(10.0, 10.0),  # Fixed values for easier testing
            min_delay=(0.0, 0.0),
            pool_size_threshold=100,
        )

        # At 0%, should be base_delay
        delay_0 = config.get_delay("test", pool_size=0)
        assert delay_0 == 10.0

        # At 50%, should be halfway
        delay_50 = config.get_delay("test", pool_size=50)
        assert delay_50 == 5.0

        # At 100%, should be min_delay
        delay_100 = config.get_delay("test", pool_size=100)
        assert delay_100 == 0.0


@pytest.mark.unit
class TestRateLimitDecorator:
    """Test rate_limit decorator"""

    def test_decorator_applies_delay(self):
        """Test that decorator adds delay before method execution"""

        class MockClient:
            def __init__(self):
                self.rate_limit = RateLimitConfig(
                    base_delay=(0.1, 0.15),  # Small delay for fast test
                    min_delay=(0.05, 0.08),
                    disable_delay=False,
                )
                self.logger = MagicMock()

            def get_proxy_pool_size(self):
                return 0

            @rate_limit()
            def test_method(self):
                return "success"

        client = MockClient()
        start_time = time.time()
        result = client.test_method()
        elapsed = time.time() - start_time

        assert result == "success"
        assert elapsed >= 0.1  # Should have delayed at least base_delay min

    def test_decorator_with_disabled_delay(self):
        """Test that decorator skips delay when disabled"""

        class MockClient:
            def __init__(self):
                self.rate_limit = RateLimitConfig(disable_delay=True)
                self.logger = MagicMock()

            def get_proxy_pool_size(self):
                return 0

            @rate_limit()
            def test_method(self):
                return "success"

        client = MockClient()
        start_time = time.time()
        result = client.test_method()
        elapsed = time.time() - start_time

        assert result == "success"
        assert elapsed < 0.01  # Should be instant

    def test_decorator_adjusts_to_pool_size(self):
        """Test that decorator adjusts delay based on pool size"""

        class MockClient:
            def __init__(self, pool_size):
                self.pool_size = pool_size
                self.rate_limit = RateLimitConfig(
                    base_delay=(0.2, 0.25),
                    min_delay=(0.05, 0.08),
                    pool_size_threshold=10,
                )
                self.logger = MagicMock()

            def get_proxy_pool_size(self):
                return self.pool_size

            @rate_limit()
            def test_method(self):
                return "success"

        # Test with no pool (should be slower)
        client_no_pool = MockClient(pool_size=0)
        start_no_pool = time.time()
        client_no_pool.test_method()
        elapsed_no_pool = time.time() - start_no_pool

        # Test with large pool (should be faster)
        client_large_pool = MockClient(pool_size=20)
        start_large_pool = time.time()
        client_large_pool.test_method()
        elapsed_large_pool = time.time() - start_large_pool

        # Large pool should be faster than no pool
        assert elapsed_large_pool < elapsed_no_pool

    def test_decorator_with_custom_method_name(self):
        """Test decorator with custom method name"""

        class MockClient:
            def __init__(self):
                self.rate_limit = RateLimitConfig(
                    base_delay=(0.1, 0.15),
                    method_multipliers={"custom_name": 0.5},
                    disable_delay=False,
                )
                self.logger = MagicMock()

            def get_proxy_pool_size(self):
                return 0

            @rate_limit("custom_name")
            def test_method(self):
                return "success"

        client = MockClient()
        result = client.test_method()
        assert result == "success"

    def test_decorator_logs_delay_info(self):
        """Test that decorator logs delay information"""

        class MockClient:
            def __init__(self):
                self.rate_limit = RateLimitConfig(
                    base_delay=(0.05, 0.08), disable_delay=False
                )
                self.logger = MagicMock()

            def get_proxy_pool_size(self):
                return 5

            @rate_limit()
            def test_method(self):
                return "success"

        client = MockClient()
        client.test_method()

        # Check that debug log was called with correct format
        client.logger.debug.assert_called_once()
        log_message = client.logger.debug.call_args[0][0]
        assert "Rate limiting test_method" in log_message
        assert "pool_size=5" in log_message


@pytest.mark.unit
@responses.activate
class TestWeiboClientRateLimiting:
    """Test WeiboClient integration with rate limiting"""

    def setup_method(self):
        """Setup mock responses"""
        # Mock session initialization
        responses.add(
            responses.GET, "https://m.weibo.cn/", status=200, json={"ok": True}
        )

        # Mock search_posts API
        responses.add(
            responses.GET,
            "https://m.weibo.cn/api/container/getIndex",
            status=200,
            json={"ok": 1, "data": {"cards": []}},
        )

    def test_client_initializes_with_default_rate_limit(self):
        """Test that client initializes with default rate limit config"""
        client = WeiboClient()

        assert client.rate_limit is not None
        assert isinstance(client.rate_limit, RateLimitConfig)
        assert client.rate_limit.base_delay == (1.0, 3.0)

    def test_client_initializes_with_custom_rate_limit(self):
        """Test that client accepts custom rate limit config"""
        custom_config = RateLimitConfig(
            base_delay=(2.0, 4.0), min_delay=(0.05, 0.1), pool_size_threshold=50
        )
        client = WeiboClient(rate_limit_config=custom_config)

        assert client.rate_limit is custom_config
        assert client.rate_limit.base_delay == (2.0, 4.0)

    def test_search_posts_applies_rate_limiting(self):
        """Test that search_posts applies rate limiting"""
        config = RateLimitConfig(
            base_delay=(0.1, 0.15),
            disable_delay=False,  # Small delay for test
        )
        client = WeiboClient(rate_limit_config=config)

        start_time = time.time()
        client.search_posts("test", page=1)
        elapsed = time.time() - start_time

        # Should have delayed
        assert elapsed >= 0.1

    def test_search_posts_with_disabled_rate_limiting(self):
        """Test that search_posts can disable rate limiting"""
        config = RateLimitConfig(disable_delay=True)
        client = WeiboClient(rate_limit_config=config)

        start_time = time.time()
        client.search_posts("test", page=1)
        elapsed = time.time() - start_time

        # Should be nearly instant (only network request time)
        assert elapsed < 0.5

    def test_multiple_calls_apply_rate_limiting(self):
        """Test that multiple calls each apply rate limiting"""
        config = RateLimitConfig(base_delay=(0.05, 0.08), disable_delay=False)
        client = WeiboClient(rate_limit_config=config)

        start_time = time.time()
        client.search_posts("test1", page=1)
        client.search_posts("test2", page=1)
        elapsed = time.time() - start_time

        # Should have delayed twice
        assert elapsed >= 0.1  # At least 2 * 0.05

    def test_rate_limiting_with_proxy_pool(self):
        """Test that rate limiting adjusts based on proxy pool size"""
        # Mock proxy API
        responses.add(
            responses.GET,
            "http://proxy.api/get",
            status=200,
            json={"proxy": "http://1.2.3.4:8080"},
        )

        config = RateLimitConfig(
            base_delay=(0.2, 0.25), min_delay=(0.05, 0.08), pool_size_threshold=10
        )
        client = WeiboClient(
            proxy_api_url="http://proxy.api/get",
            proxy_pool_size=20,
            rate_limit_config=config,
        )

        # Add proxies to pool
        client.add_proxy("http://1.2.3.4:8080")
        client.add_proxy("http://2.3.4.5:8080")

        start_time = time.time()
        client.search_posts("test", page=1)
        elapsed = time.time() - start_time

        # Delay should be interpolated between base and min based on pool size
        assert elapsed >= 0.05


@pytest.mark.unit
class TestRateLimitingEdgeCases:
    """Test edge cases for rate limiting"""

    def test_zero_delay_range(self):
        """Test rate limiting with zero delay range"""
        config = RateLimitConfig(
            base_delay=(0.0, 0.0), min_delay=(0.0, 0.0), disable_delay=False
        )

        delay = config.get_delay("test", pool_size=10)
        assert delay == 0.0

    def test_negative_pool_size(self):
        """Test that negative pool size is handled"""
        config = RateLimitConfig(pool_size_threshold=20)

        # Negative pool size should be treated as 0 (use base_delay)
        delay = config.get_delay("test", pool_size=-5)
        assert 1.0 <= delay <= 3.0

    def test_very_large_pool_size(self):
        """Test handling of very large pool size"""
        config = RateLimitConfig(
            base_delay=(2.0, 4.0), min_delay=(0.1, 0.2), pool_size_threshold=20
        )

        # Pool size much larger than threshold should still use min_delay
        delay = config.get_delay("test", pool_size=10000)
        assert 0.1 <= delay <= 0.2

    def test_extreme_multipliers(self):
        """Test extreme method multipliers"""
        config = RateLimitConfig(
            base_delay=(1.0, 2.0), method_multipliers={"zero": 0.0, "huge": 100.0}
        )

        # Zero multiplier should give zero delay
        zero_delay = config.get_delay("zero", pool_size=0)
        assert zero_delay == 0.0

        # Huge multiplier
        huge_delay = config.get_delay("huge", pool_size=0)
        assert 100.0 <= huge_delay <= 200.0
