#!/usr/bin/env python

"""
代理池管理器
"""

import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import requests


@dataclass
class ProxyPoolConfig:
    """代理池配置类"""

    proxy_api_url: Optional[str] = None
    """动态代理API地址"""

    proxy_api_parser: Optional[Callable[[dict], str]] = None
    """自定义代理API响应解析函数"""

    dynamic_proxy_ttl: int = 300
    """动态代理的过期时间（秒），默认300秒（5分钟）"""

    pool_size: int = 10
    """IP池容量，默认10个"""

    fetch_strategy: str = "random"
    """代理获取策略：'random'(随机) 或 'round_robin'(轮询)，默认random"""


class ProxyPool:
    """代理池管理器，支持动态和静态IP统一管理"""

    def __init__(self, config: Optional[ProxyPoolConfig] = None):
        """
        初始化代理池

        Args:
            config: 代理池配置对象，如果为None则使用默认配置
        """
        self.config = config or ProxyPoolConfig()

        # IP池: List[(proxy_url, expire_time)]
        self._proxy_pool: List[Tuple[str, float]] = []
        self._current_index = 0

    def _default_api_parser(self, response_data: dict) -> str:
        """
        默认的代理API响应解析器

        支持以下格式:
        - {"ip": "1.2.3.4", "port": "8080"}
        - {"proxy": "http://1.2.3.4:8080"}
        - {"data": {"ip": "1.2.3.4", "port": 8080}}
        """
        if "proxy" in response_data:
            return response_data["proxy"]

        data = response_data.get("data", response_data)

        if "ip" in data and "port" in data:
            ip = data["ip"]
            port = data["port"]
            # 如果有认证信息
            if "username" in data and "password" in data:
                username = data["username"]
                password = data["password"]
                return f"http://{username}:{password}@{ip}:{port}"
            return f"http://{ip}:{port}"

        raise ValueError(f"无法解析代理API响应: {response_data}")

    def add_proxy(self, proxy_url: str, ttl: Optional[int] = None):
        """
        手动添加静态代理到IP池

        Args:
            proxy_url: 代理URL，格式如 'http://1.2.3.4:8080' 或 'http://user:pass@ip:port'
            ttl: 过期时间（秒），None表示永不过期
        """
        expire_time = time.time() + ttl if ttl is not None else float("inf")
        self._proxy_pool.append((proxy_url, expire_time))

    def _fetch_proxy_from_api(self) -> Optional[str]:
        """从代理API获取一个新的代理URL"""
        if not self.config.proxy_api_url:
            return None

        try:
            response = requests.get(self.config.proxy_api_url, timeout=5)
            response.raise_for_status()
            proxy_data = response.json()
            parser = self.config.proxy_api_parser or self._default_api_parser
            return parser(proxy_data)
        except Exception:
            return None

    def _clean_expired_proxies(self):
        """清理过期的代理"""
        current_time = time.time()
        self._proxy_pool = [
            (proxy_url, expire_time)
            for proxy_url, expire_time in self._proxy_pool
            if expire_time > current_time
        ]

    def _is_pool_full(self) -> bool:
        """检查IP池是否已满"""
        return len(self._proxy_pool) >= self.config.pool_size

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取一个可用的代理

        策略：
        1. 清理过期代理
        2. 如果IP池未满，尝试从动态API获取新代理加入池
        3. 如果IP池已满，根据策略（随机/轮询）从池中选择代理
        4. 如果池为空且无法获取新代理，返回None

        Returns:
            代理字典，格式为 {'http': 'http://...', 'https': 'http://...'}
            如果没有可用代理则返回 None
        """
        # 清理过期代理
        self._clean_expired_proxies()

        # 如果IP池未满，尝试从API获取新代理
        if not self._is_pool_full():
            proxy_url = self._fetch_proxy_from_api()
            if proxy_url:
                self.add_proxy(proxy_url, ttl=self.config.dynamic_proxy_ttl)

        # 从IP池获取代理
        if self._proxy_pool:
            if self.config.fetch_strategy == "random":
                # 随机选择
                proxy_url, _ = random.choice(self._proxy_pool)
            else:
                # 轮询选择
                proxy_url, _ = self._proxy_pool[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._proxy_pool)
            return {"http": proxy_url, "https": proxy_url}

        return None

    def get_pool_size(self) -> int:
        """
        获取当前IP池大小（不含过期代理）

        Returns:
            可用代理数量
        """
        self._clean_expired_proxies()
        return len(self._proxy_pool)

    def clear_pool(self):
        """清空IP池"""
        self._proxy_pool = []
        self._current_index = 0

    def is_enabled(self) -> bool:
        """
        检查代理池是否启用

        Returns:
            如果配置了动态API或IP池中有代理则返回True
        """
        self._clean_expired_proxies()
        return bool(self.config.proxy_api_url or self._proxy_pool)

    def get_pool_capacity(self) -> int:
        """
        获取IP池容量

        Returns:
            IP池最大容量
        """
        return self.config.pool_size
