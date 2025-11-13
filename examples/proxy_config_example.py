#!/usr/bin/env python
"""
Example: Using ProxyPoolConfig with WeiboClient

This example demonstrates the new proxy configuration API.
"""

from crawl4weibo import ProxyPoolConfig, WeiboClient


def example_basic_proxy():
    """Example 1: Basic proxy configuration"""
    print("=" * 60)
    print("Example 1: Basic Proxy Configuration")
    print("=" * 60)

    proxy_config = ProxyPoolConfig(proxy_api_url="http://api.proxy.com/get")

    client = WeiboClient(proxy_config=proxy_config)
    print(f"Client initialized with proxy pool size: {client.get_proxy_pool_size()}")
    print()


def example_custom_pool_settings():
    """Example 2: Custom pool size, TTL, and strategy"""
    print("=" * 60)
    print("Example 2: Custom Pool Settings")
    print("=" * 60)

    proxy_config = ProxyPoolConfig(
        proxy_api_url="http://api.proxy.com/get",
        pool_size=20,  # Larger pool for high-volume scraping
        dynamic_proxy_ttl=600,  # 10 minutes TTL
        fetch_strategy="round_robin",  # Use proxies in rotation
    )

    client = WeiboClient(proxy_config=proxy_config)
    print(f"Pool capacity: {client.proxy_pool.get_pool_capacity()}")
    print(f"Fetch strategy: {client.proxy_pool.config.fetch_strategy}")
    print(f"TTL: {client.proxy_pool.config.dynamic_proxy_ttl}s")
    print()


def example_one_time_proxy():
    """Example 3: One-time proxy mode (for single-use IP providers)"""
    print("=" * 60)
    print("Example 3: One-Time Proxy Mode")
    print("=" * 60)

    proxy_config = ProxyPoolConfig(
        proxy_api_url="http://api.proxy.com/get", use_once_proxy=True
    )

    client = WeiboClient(proxy_config=proxy_config)
    print("One-time proxy mode enabled")
    print("Each request will use a fresh proxy IP")
    print(f"Is enabled: {client.proxy_pool.is_enabled()}")
    print()


def example_custom_parser():
    """Example 4: Custom proxy parser"""
    print("=" * 60)
    print("Example 4: Custom Proxy Parser")
    print("=" * 60)

    def custom_parser(data):
        """Parse custom proxy API response format"""
        # Example: API returns {"success": true, "proxies": [{"ip": "...", "port": "..."}]}
        if isinstance(data, dict) and "proxies" in data:
            return [f"http://{item['ip']}:{item['port']}" for item in data["proxies"]]
        return []

    proxy_config = ProxyPoolConfig(
        proxy_api_url="http://api.proxy.com/get", proxy_api_parser=custom_parser
    )

    client = WeiboClient(proxy_config=proxy_config)
    print("Client initialized with custom proxy parser")
    print()


def example_no_proxy():
    """Example 5: No proxy (default)"""
    print("=" * 60)
    print("Example 5: No Proxy (Default)")
    print("=" * 60)

    # Simply don't pass proxy_config
    client = WeiboClient()
    print(f"Proxy enabled: {client.proxy_pool.is_enabled()}")
    print("Using direct connection (no proxy)")
    print()


def example_manual_proxy_management():
    """Example 6: Manual proxy addition and management"""
    print("=" * 60)
    print("Example 6: Manual Proxy Management")
    print("=" * 60)

    # Start without proxy API
    client = WeiboClient()

    # Add static proxies manually
    client.add_proxy("http://1.2.3.4:8080", ttl=300)  # 5 minutes TTL
    client.add_proxy("http://5.6.7.8:9090", ttl=None)  # Never expires
    client.add_proxy("http://user:pass@10.11.12.13:3128", ttl=600)  # With auth

    print(f"Current pool size: {client.get_proxy_pool_size()}")

    # Clear pool when needed
    client.clear_proxy_pool()
    print(f"Pool size after clear: {client.get_proxy_pool_size()}")
    print()


def example_config_reuse():
    """Example 7: Reusing configuration across multiple clients"""
    print("=" * 60)
    print("Example 7: Configuration Reuse")
    print("=" * 60)

    # Create config once
    shared_proxy_config = ProxyPoolConfig(
        proxy_api_url="http://api.proxy.com/get",
        pool_size=15,
        fetch_strategy="random",
    )

    # Use in multiple clients
    client1 = WeiboClient(proxy_config=shared_proxy_config)
    client2 = WeiboClient(proxy_config=shared_proxy_config)

    print("Created 2 clients with shared configuration")
    print(
        f"Client 1 pool capacity: {client1.proxy_pool.get_pool_capacity()}"
    )
    print(
        f"Client 2 pool capacity: {client2.proxy_pool.get_pool_capacity()}"
    )
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ProxyPoolConfig Examples")
    print("=" * 60 + "\n")

    # Run all examples
    example_basic_proxy()
    example_custom_pool_settings()
    example_one_time_proxy()
    example_custom_parser()
    example_no_proxy()
    example_manual_proxy_management()
    example_config_reuse()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
