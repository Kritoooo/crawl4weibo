#!/usr/bin/env python

"""
微博爬虫客户端 - 基于实际测试成功的代码
"""

import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from ..exceptions.base import CrawlError, NetworkError, ParseError, UserNotFoundError
from ..models.post import Post
from ..models.user import User
from ..utils.downloader import ImageDownloader
from ..utils.logger import setup_logger
from ..utils.parser import WeiboParser


class WeiboClient:
    """微博爬虫客户端"""

    def __init__(
        self,
        cookies: Optional[Union[str, Dict[str, str]]] = None,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        初始化微博客户端

        Args:
            cookies: 可选的Cookie字符串或字典
            log_level: 日志级别
            log_file: 日志文件路径
            user_agent: 可选的User-Agent字符串
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
        self, url: str, params: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=5)

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

    def get_user_by_uid(self, uid: str) -> User:
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100505{uid}"}

        data = self._request(url, params)

        if not data.get("data") or not data["data"].get("userInfo"):
            raise UserNotFoundError(f"用户 {uid} 不存在")

        user_info = self.parser.parse_user_info(data)
        user = User.from_dict(user_info)

        self.logger.info(f"获取用户: {user.screen_name}")
        return user

    def get_user_posts(
        self, uid: str, page: int = 1, expand: bool = False
    ) -> List[Post]:
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"107603{uid}", "page": page}

        data = self._request(url, params)

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

    def get_post_by_bid(self, bid: str) -> Post:
        url = "https://m.weibo.cn/statuses/show"
        params = {"id": bid}

        data = self._request(url, params)

        if not data.get("data"):
            raise ParseError(f"未找到微博 {bid}")

        post_data = self.parser._parse_single_post(data["data"])
        if not post_data:
            raise ParseError(f"解析微博数据失败 {bid}")

        return Post.from_dict(post_data)

    def search_users(self, query: str, page: int = 1, count: int = 10) -> List[User]:
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {
            "containerid": f"100103type=3&q={query}",
            "page": page,
            "count": count,
        }

        data = self._request(url, params)
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

    def search_posts(self, query: str, page: int = 1) -> List[Post]:
        time.sleep(random.uniform(1, 3))

        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100103type=1&q={query}", "page": page}

        data = self._request(url, params)
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
