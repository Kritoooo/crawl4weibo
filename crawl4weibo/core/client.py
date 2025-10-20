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
        posts = [Post.from_dict(post_data) for post_data in posts_data]
        for post in posts:
            if post.is_long_text and expand:
                try:
                    long_post = self.get_post_by_bid(post.bid)
                    post.text = long_post.text
                    post.pic_urls = long_post.pic_urls
                    post.video_url = long_post.video_url
                except Exception as e:
                    self.logger.warning(f"展开长微博失败 {post.bid}: {e}")

        self.logger.info(f"获取到 {len(posts)} 条微博")
        return posts

    def get_post_by_bid(self, bid: str, use_proxy: bool = True) -> Post:
        """
        根据bid获取微博详情

        Args:
            bid: 微博bid
            use_proxy: 是否使用代理，默认True

        Returns:
            Post对象
        """
        url = "https://m.weibo.cn/statuses/show"
        params = {"id": bid}

        data = self._request(url, params, use_proxy=use_proxy)

        if not data.get("data"):
            raise ParseError(f"未找到微博 {bid}")

        post_data = self.parser._parse_single_post(data["data"])
        if not post_data:
            raise ParseError(f"解析微博数据失败 {bid}")

        return Post.from_dict(post_data)

    def search_users(
        self, query: str, page: int = 1, count: int = 10, use_proxy: bool = True
    ) -> List[User]:
        """
        搜索用户

        Args:
            query: 搜索关键词
            page: 页码
            count: 每页数量
            use_proxy: 是否使用代理，默认True

        Returns:
            User对象列表
        """
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {
            "containerid": f"100103type=3&q={query}",
            "page": page,
            "count": count,
        }

        data = self._request(url, params, use_proxy=use_proxy)
        users = []
        cards = data.get("data", {}).get("cards", [])

        for card in cards:
            if card.get("card_type") == 11:
                card_group = card.get("card_group", [])
                for group_card in card_group:
                    if group_card.get("card_type") == 10:
                        user_data = group_card.get("user", {})
                        if user_data:
                            users.append(User.from_dict(user_data))

        self.logger.info(f"搜索到 {len(users)} 个用户")
        return users

    def search_posts(
        self, query: str, page: int = 1, use_proxy: bool = True
    ) -> List[Post]:
        """
        搜索微博

        Args:
            query: 搜索关键词
            page: 页码
            use_proxy: 是否使用代理，默认True

        Returns:
            Post对象列表
        """
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100103type=1&q={query}", "page": page}

        data = self._request(url, params, use_proxy=use_proxy)
        posts_data = self.parser.parse_posts(data)
        posts = [Post.from_dict(post_data) for post_data in posts_data]

        self.logger.info(f"搜索到 {len(posts)} 条微博")
        return posts

    def download_post_images(
        self,
        post: Post,
        download_dir: Optional[str] = None,
        subdir: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Download images from a single post

        Args:
            post: Post object containing image URLs
            download_dir: Custom download directory (optional)
            subdir: Subdirectory name for organizing downloads

        Returns:
            Dictionary mapping image URLs to downloaded file paths
        """
        if download_dir:
            self.downloader.download_dir = Path(download_dir)
            self.downloader.download_dir.mkdir(parents=True, exist_ok=True)

        if not post.pic_urls:
            self.logger.info(f"Post {post.id} has no images to download")
            return {}

        return self.downloader.download_post_images(post.pic_urls, post.id, subdir)

    def download_posts_images(
        self,
        posts: List[Post],
        download_dir: Optional[str] = None,
        subdir: Optional[str] = None,
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Download images from multiple posts

        Args:
            posts: List of Post objects
            download_dir: Custom download directory (optional)
            subdir: Subdirectory name for organizing downloads

        Returns:
            Dictionary mapping post IDs to their download results
        """
        if download_dir:
            self.downloader.download_dir = Path(download_dir)
            self.downloader.download_dir.mkdir(parents=True, exist_ok=True)

        posts_with_images = [post for post in posts if post.pic_urls]
        if not posts_with_images:
            self.logger.info("No posts with images found")
            return {}

        self.logger.info(
            f"Found {len(posts_with_images)} posts with images "
            f"out of {len(posts)} total posts"
        )
        return self.downloader.download_posts_images(posts_with_images, subdir)

    def download_user_posts_images(
        self,
        uid: str,
        pages: int = 1,
        download_dir: Optional[str] = None,
        expand_long_text: bool = False,
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Download images from user's posts

        Args:
            uid: User ID
            pages: Number of pages to fetch
            download_dir: Custom download directory (optional)
            expand_long_text: Whether to expand long text posts

        Returns:
            Dictionary mapping post IDs to their download results
        """
        all_posts = []

        for page in range(1, pages + 1):
            posts = self.get_user_posts(uid, page=page, expand=expand_long_text)
            if not posts:
                break
            all_posts.extend(posts)

            if page < pages:
                time.sleep(random.uniform(2, 4))

        subdir = f"user_{uid}"

        return self.download_posts_images(all_posts, download_dir, subdir)
