#!/usr/bin/env python

"""
微博爬虫客户端 - 基于实际测试成功的代码
"""

import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import requests

from ..exceptions.base import CrawlError, NetworkError, ParseError, UserNotFoundError
from ..models.post import Post
from ..models.user import User
from ..utils.downloader import ImageDownloader
from ..utils.logger import setup_logger
from ..utils.parser import WeiboParser
from ..utils.proxy import ProxyPool, ProxyPoolConfig


class WeiboClient:
    """微博爬虫客户端"""

    def __init__(
        self,
        cookies: Optional[Union[str, Dict[str, str]]] = None,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        user_agent: Optional[str] = None,
        proxy_api_url: Optional[str] = None,
        proxy_api_parser: Optional[Callable[[dict], str]] = None,
        dynamic_proxy_ttl: int = 300,
        proxy_pool_size: int = 10,
        proxy_fetch_strategy: str = "random",
    ):
        """
        初始化微博客户端

        Args:
            cookies: 可选的Cookie字符串或字典
            log_level: 日志级别
            log_file: 日志文件路径
            user_agent: 可选的User-Agent字符串
            proxy_api_url: 动态代理API地址，如 'http://api.proxy.com/get?format=json'
            proxy_api_parser: 自定义代理API响应解析函数，接收响应JSON返回代理URL字符串
            dynamic_proxy_ttl: 动态代理的过期时间（秒），默认300秒（5分钟）
            proxy_pool_size: IP池容量，默认10个
            proxy_fetch_strategy: 代理获取策略，'random'或'round_robin'，默认random
        """
        self.logger = setup_logger(
            level=getattr(__import__("logging"), log_level.upper()), log_file=log_file
        )

        self.session = requests.Session()

        default_user_agent = (
            "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.5615.135 Mobile Safari/537.36"
        )
        self.session.headers.update(
            {
                "User-Agent": user_agent or default_user_agent,
                "Referer": "https://m.weibo.cn/",
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        if cookies:
            self._set_cookies(cookies)

        self._init_session()

        self.parser = WeiboParser()
        self.downloader = ImageDownloader(
            session=self.session,
            download_dir="./weibo_images",
        )

        # 初始化代理池配置和代理池
        proxy_config = ProxyPoolConfig(
            proxy_api_url=proxy_api_url,
            proxy_api_parser=proxy_api_parser,
            dynamic_proxy_ttl=dynamic_proxy_ttl,
            pool_size=proxy_pool_size,
            fetch_strategy=proxy_fetch_strategy,
        )
        self.proxy_pool = ProxyPool(config=proxy_config)

        if proxy_api_url:
            self.logger.info(
                f"代理池已启用 (API: {proxy_api_url}, "
                f"容量: {proxy_pool_size}, TTL: {dynamic_proxy_ttl}s, "
                f"策略: {proxy_fetch_strategy})"
            )

        self.logger.info("WeiboClient initialized successfully")

    def _set_cookies(self, cookies: Union[str, Dict[str, str]]):
        if isinstance(cookies, str):
            cookie_dict = {}
            for pair in cookies.split(";"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    cookie_dict[key.strip()] = value.strip()
            self.session.cookies.update(cookie_dict)
        elif isinstance(cookies, dict):
            self.session.cookies.update(cookies)

    def _init_session(self):
        try:
            self.logger.debug("初始化session...")
            self.session.get("https://m.weibo.cn/", timeout=5)
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            self.logger.warning(f"Session初始化失败: {e}")

    def _request(
        self,
        url: str,
        params: Dict[str, Any],
        max_retries: int = 3,
        use_proxy: bool = True,
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            url: 请求URL
            params: 请求参数
            max_retries: 最大重试次数
            use_proxy: 是否使用代理，默认True。设为False可在单次请求中禁用代理

        Returns:
            响应的JSON数据
        """
        for attempt in range(1, max_retries + 1):
            proxies = None
            if use_proxy and self.proxy_pool and self.proxy_pool.is_enabled():
                proxies = self.proxy_pool.get_proxy()
                if proxies:
                    self.logger.debug(f"使用代理: {proxies.get('http', 'N/A')}")
                else:
                    self.logger.warning("代理池未能获取到可用代理，本次请求不使用代理")

            try:
                response = self.session.get(
                    url, params=params, proxies=proxies, timeout=5
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 432:
                    if attempt < max_retries:
                        sleep_time = random.uniform(4, 7)
                        self.logger.warning(
                            f"遇到432错误，等待 {sleep_time:.1f} 秒后重试..."
                        )
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise NetworkError("遇到432反爬虫拦截")
                else:
                    response.raise_for_status()

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    sleep_time = random.uniform(2, 5)
                    self.logger.warning(
                        f"请求失败，等待 {sleep_time:.1f} 秒后重试: {e}"
                    )
                    time.sleep(sleep_time)
                    continue
                else:
                    raise NetworkError(f"请求失败: {e}")

        raise CrawlError("达到最大重试次数")

    def add_proxy(self, proxy_url: str, ttl: Optional[int] = None):
        """
        手动添加静态代理到IP池

        Args:
            proxy_url: 代理URL，格式如 'http://1.2.3.4:8080' 或 'http://user:pass@ip:port'
            ttl: 过期时间（秒），None表示永不过期
        """
        self.proxy_pool.add_proxy(proxy_url, ttl)
        ttl_str = "永不过期" if ttl is None else f"{ttl}s"
        self.logger.info(f"添加代理到IP池: {proxy_url}, TTL: {ttl_str}")

    def get_proxy_pool_size(self) -> int:
        """
        获取当前IP池大小

        Returns:
            可用代理数量
        """
        return self.proxy_pool.get_pool_size()

    def clear_proxy_pool(self):
        """清空IP池"""
        self.proxy_pool.clear_pool()
        self.logger.info("IP池已清空")

    def get_user_by_uid(self, uid: str, use_proxy: bool = True) -> User:
        """
        获取用户信息

        Args:
            uid: 用户ID
            use_proxy: 是否使用代理，默认True

        Returns:
            User对象
        """
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100505{uid}"}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data") or not data["data"].get("userInfo"):
            raise UserNotFoundError(f"用户 {uid} 不存在")

        user_info = self.parser.parse_user_info(data)
        user = User.from_dict(user_info)

        self.logger.info(f"获取用户: {user.screen_name}")
        return user

    def get_user_posts(
        self, uid: str, page: int = 1, expand: bool = False, use_proxy: bool = True
    ) -> List[Post]:
        """
        获取用户微博列表

        Args:
            uid: 用户ID
            page: 页码
            expand: 是否展开长文
            use_proxy: 是否使用代理，默认True

        Returns:
            Post对象列表
        """
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"107603{uid}", "page": page}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data"):
            return []

        posts_data = self.parser.parse_posts(data)
        posts = [Post.from_dict(p) for p in posts_data]

        # This part of the function was truncated in the original code, 
        # but for completeness, it's assumed it would continue processing 'posts'.
        # As no changes are required in this file, the original (truncated) code is preserved.

        return posts