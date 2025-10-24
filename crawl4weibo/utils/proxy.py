#!/usr/bin/env python

"""
Proxy pool manager
"""

import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import requests


@dataclass
class ProxyPoolConfig:
    """Proxy pool configuration class"""

    proxy_api_url: Optional[str] = None
    """Dynamic proxy API URL"""

    proxy_api_parser: Optional[Callable[[dict], str]] = None
    """Custom proxy API response parser function"""

    dynamic_proxy_ttl: int = 300
    """Dynamic proxy expiration time (seconds), default 300 seconds (5 minutes)"""

    pool_size: int = 10
    """Proxy pool capacity, default 10"""

    fetch_strategy: str = "random"
    """Proxy fetch strategy: 'random' or 'round_robin', default random"""


class ProxyPool:
    """Proxy pool manager, supports unified management of dynamic and static proxies"""

    def __init__(self, config: Optional[ProxyPoolConfig] = None):
        """
        Initialize proxy pool

        Args:
            config: Proxy pool configuration object, if None will use
                default configuration
        """
        self.config = config or ProxyPoolConfig()

        # Proxy pool: List[(proxy_url, expire_time)]
        self._proxy_pool: List[Tuple[str, float]] = []
        self._current_index = 0

    def _default_api_parser(self, response_data) -> str:
        """
        Default proxy API response parser

        Supports the following formats:
        - Plain text: "218.95.37.11:25152" or multiple lines
        - Plain text with auth: "218.95.37.11:25152:username:password"
        - JSON: {"ip": "1.2.3.4", "port": "8080"}
        - JSON: {"proxy": "http://1.2.3.4:8080"}
        - JSON: {"data": {"ip": "1.2.3.4", "port": 8080}}
        - JSON: {"data": [{"ip": "1.2.3.4", "port": 8080}]}
        - JSON: {"data": ["218.95.37.11:25152:username:password", ...]}
        - JSON with auth:
          {"ip": "...", "port": "...", "username": "...", "password": "..."}
        """
        if isinstance(response_data, str):
            lines = [line.strip() for line in response_data.split("\n") if line.strip()]
            if not lines:
                raise ValueError("Proxy API returned empty text response")

            proxy_str = lines[0]

            if proxy_str.startswith(("http://", "https://", "socks4://", "socks5://")):
                parts = proxy_str.split("://", 1)
                if len(parts) == 2 and ":" in parts[1]:
                    return proxy_str
                else:
                    raise ValueError(f"Invalid proxy format: {proxy_str}")
            else:
                if ":" not in proxy_str:
                    raise ValueError(
                        f"Invalid proxy format (missing port): {proxy_str}"
                    )

                parts = proxy_str.split(":")

                # Validate port number
                def validate_port(port_str: str):
                    try:
                        port_num = int(port_str)
                        if not (1 <= port_num <= 65535):
                            raise ValueError(f"Invalid port number: {port_str}")
                    except ValueError:
                        raise ValueError(
                            f"Invalid proxy format (invalid port): {proxy_str}"
                        )

                if len(parts) == 4:
                    host, port, username, password = parts
                    validate_port(port)
                    return f"http://{username}:{password}@{host}:{port}"

                elif len(parts) == 2:
                    host, port = parts
                    validate_port(port)
                    return f"http://{proxy_str}"
                else:
                    raise ValueError(f"Invalid proxy format: {proxy_str}")

        if isinstance(response_data, dict):
            if "proxy" in response_data:
                return response_data["proxy"]

            data = response_data.get("data", response_data)

            if isinstance(data, list):
                if not data:
                    raise ValueError(
                        f"Proxy API returned empty data array: {response_data}"
                    )
                first_item = data[0]

                if isinstance(first_item, str):
                    return self._default_api_parser(first_item)

                data = first_item

            if isinstance(data, dict) and "ip" in data and "port" in data:
                ip = data["ip"]
                port = data["port"]
                if "username" in data and "password" in data:
                    username = data["username"]
                    password = data["password"]
                    return f"http://{username}:{password}@{ip}:{port}"
                return f"http://{ip}:{port}"

        raise ValueError(f"Unable to parse proxy API response: {response_data}")

    def add_proxy(self, proxy_url: str, ttl: Optional[int] = None):
        """
        Manually add static proxy to proxy pool

        Args:
            proxy_url: Proxy URL, format like 'http://1.2.3.4:8080' or 'http://user:pass@ip:port'
            ttl: Expiration time (seconds), None means never expires
        """
        expire_time = time.time() + ttl if ttl is not None else float("inf")
        self._proxy_pool.append((proxy_url, expire_time))

    def _fetch_proxy_from_api(self) -> Optional[str]:
        """Fetch a new proxy URL from proxy API"""
        if not self.config.proxy_api_url:
            return None

        try:
            response = requests.get(self.config.proxy_api_url, timeout=5)
            response.raise_for_status()

            try:
                proxy_data = response.json()
            except ValueError:
                proxy_data = response.text

            parser = self.config.proxy_api_parser or self._default_api_parser
            return parser(proxy_data)
        except Exception:
            return None

    def _clean_expired_proxies(self):
        """Clean up expired proxies"""
        current_time = time.time()
        self._proxy_pool = [
            (proxy_url, expire_time)
            for proxy_url, expire_time in self._proxy_pool
            if expire_time > current_time
        ]

    def _is_pool_full(self) -> bool:
        """Check if proxy pool is full"""
        return len(self._proxy_pool) >= self.config.pool_size

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get an available proxy

        Strategy:
        1. Clean up expired proxies
        2. If proxy pool is not full, try to fetch new proxy from dynamic
           API and add to pool
        3. If proxy pool is full, select proxy from pool based on strategy
           (random/round-robin)
        4. If pool is empty and cannot fetch new proxy, return None

        Returns:
            Proxy dictionary, format: {'http': 'http://...', 'https': 'http://...'}
            Returns None if no proxy is available
        """
        self._clean_expired_proxies()

        if not self._is_pool_full():
            proxy_url = self._fetch_proxy_from_api()
            if proxy_url:
                self.add_proxy(proxy_url, ttl=self.config.dynamic_proxy_ttl)

        if self._proxy_pool:
            if self.config.fetch_strategy == "random":
                proxy_url, _ = random.choice(self._proxy_pool)
            else:
                proxy_url, _ = self._proxy_pool[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._proxy_pool)
            return {"http": proxy_url, "https": proxy_url}

        return None

    def get_pool_size(self) -> int:
        """
        Get current proxy pool size (excluding expired proxies)

        Returns:
            Number of available proxies
        """
        self._clean_expired_proxies()
        return len(self._proxy_pool)

    def clear_pool(self):
        """Clear proxy pool"""
        self._proxy_pool = []
        self._current_index = 0

    def is_enabled(self) -> bool:
        """
        Check if proxy pool is enabled

        Returns:
            True if dynamic API is configured or there are proxies in the pool
        """
        self._clean_expired_proxies()
        return bool(self.config.proxy_api_url or self._proxy_pool)

    def get_pool_capacity(self) -> int:
        """
        Get proxy pool capacity

        Returns:
            Maximum proxy pool capacity
        """
        return self.config.pool_size
