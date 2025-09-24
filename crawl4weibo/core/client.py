#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
微博爬虫客户端 - 基于实际测试成功的代码
"""

import requests
import time
import random
from typing import List, Dict, Any, Optional, Union

from ..utils.parser import WeiboParser
from ..utils.logger import setup_logger
from ..models.user import User
from ..models.post import Post
from ..exceptions.base import CrawlError, UserNotFoundError, ParseError, NetworkError


class WeiboClient:
    """微博爬虫客户端"""
    
    def __init__(self, cookies: Optional[Union[str, Dict[str, str]]] = None,
                 log_level: str = "INFO", log_file: Optional[str] = None,
                 user_agent: Optional[str] = None):
        """
        初始化微博客户端
        
        Args:
            cookies: 可选的Cookie字符串或字典
            log_level: 日志级别
            log_file: 日志文件路径
            user_agent: 可选的User-Agent字符串
        """
        self.logger = setup_logger(
            level=getattr(__import__('logging'), log_level.upper()),
            log_file=log_file
        )
        
        # 创建session
        self.session = requests.Session()
        
        # 设置经过验证的headers
        default_user_agent = (
            "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.5615.135 Mobile Safari/537.36"
        )
        self.session.headers.update({
            "User-Agent": user_agent or default_user_agent,
            "Referer": "https://m.weibo.cn/",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest"
        })
        
        # 添加Cookie（如果提供）
        if cookies:
            self._set_cookies(cookies)
        
        # 初始化session
        self._init_session()
        
        # 解析器
        self.parser = WeiboParser()
        
        self.logger.info("WeiboClient initialized successfully")
    
    def _set_cookies(self, cookies: Union[str, Dict[str, str]]):
        """设置cookies"""
        if isinstance(cookies, str):
            cookie_dict = {}
            for pair in cookies.split(';'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    cookie_dict[key.strip()] = value.strip()
            self.session.cookies.update(cookie_dict)
        elif isinstance(cookies, dict):
            self.session.cookies.update(cookies)
    
    def _init_session(self):
        """初始化session，获取首页cookie"""
        try:
            self.logger.debug("初始化session...")
            self.session.get("https://m.weibo.cn/", timeout=5)
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            self.logger.warning(f"Session初始化失败: {e}")
    
    def _request(self, url: str, params: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """发送请求并处理重试"""
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 432:
                    if attempt < max_retries:
                        sleep_time = random.uniform(4, 7)
                        self.logger.warning(f"遇到432错误，等待 {sleep_time:.1f} 秒后重试...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise NetworkError("遇到432反爬虫拦截")
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    sleep_time = random.uniform(2, 5)
                    self.logger.warning(f"请求失败，等待 {sleep_time:.1f} 秒后重试: {e}")
                    time.sleep(sleep_time)
                    continue
                else:
                    raise NetworkError(f"请求失败: {e}")
        
        raise CrawlError("达到最大重试次数")
    
    def get_user_by_uid(self, uid: str) -> User:
        """根据UID获取用户信息"""
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"100505{uid}"}
        
        data = self._request(url, params)
        
        if not data.get("data") or not data["data"].get("userInfo"):
            raise UserNotFoundError(f"用户 {uid} 不存在")
        
        user_info = self.parser.parse_user_info(data)
        user = User.from_dict(user_info)
        
        self.logger.info(f"获取用户: {user.screen_name}")
        return user
    
    def get_user_posts(self, uid: str, page: int = 1) -> List[Post]:
        """获取用户微博"""
        time.sleep(random.uniform(1, 3))  # 请求间隔
        
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {"containerid": f"107603{uid}", "page": page}
        
        data = self._request(url, params)
        
        if not data.get("data"):
            return []
        
        posts_data = self.parser.parse_posts(data)
        posts = [Post.from_dict(post_data) for post_data in posts_data]
        
        self.logger.info(f"获取到 {len(posts)} 条微博")
        return posts
    
    def search_users(self, query: str, page: int = 1, count: int = 10) -> List[User]:
        """搜索用户"""
        time.sleep(random.uniform(1, 3))
        
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {
            "containerid": f"100103type=3&q={query}",
            "page": page,
            "count": count
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
        """搜索微博"""
        time.sleep(random.uniform(1, 3))
        
        url = "https://m.weibo.cn/api/container/getIndex"
        params = {
            "containerid": f"100103type=1&q={query}",
            "page": page
        }
        
        data = self._request(url, params)
        posts_data = self.parser.parse_posts(data)
        posts = [Post.from_dict(post_data) for post_data in posts_data]
        
        self.logger.info(f"搜索到 {len(posts)} 条微博")
        return posts