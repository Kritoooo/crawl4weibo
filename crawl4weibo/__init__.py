#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
crawl4weibo - A professional Weibo crawler library
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.client import WeiboClient
from .models.user import User
from .models.post import Post
from .exceptions.base import CrawlError, AuthenticationError, RateLimitError, UserNotFoundError, NetworkError, ParseError

__all__ = [
    "WeiboClient",
    "User", 
    "Post",
    "CrawlError",
    "AuthenticationError", 
    "RateLimitError",
    "UserNotFoundError",
    "NetworkError", 
    "ParseError",
]