#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base exceptions for crawl4weibo
"""


class CrawlError(Exception):
    """Base exception for crawl4weibo"""
    
    def __init__(self, message="An error occurred during crawling", code=None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthenticationError(CrawlError):
    """Raised when authentication fails"""
    
    def __init__(self, message="Authentication failed", code="AUTH_ERROR"):
        super().__init__(message, code)


class RateLimitError(CrawlError):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message="Rate limit exceeded", code="RATE_LIMIT", retry_after=None):
        self.retry_after = retry_after
        super().__init__(message, code)


class NetworkError(CrawlError):
    """Raised when network request fails"""
    
    def __init__(self, message="Network request failed", code="NETWORK_ERROR"):
        super().__init__(message, code)


class ParseError(CrawlError):
    """Raised when response parsing fails"""
    
    def __init__(self, message="Failed to parse response", code="PARSE_ERROR"):
        super().__init__(message, code)


class UserNotFoundError(CrawlError):
    """Raised when user is not found"""
    
    def __init__(self, message="User not found", code="USER_NOT_FOUND"):
        super().__init__(message, code)


class InvalidConfigError(CrawlError):
    """Raised when configuration is invalid"""
    
    def __init__(self, message="Invalid configuration", code="INVALID_CONFIG"):
        super().__init__(message, code)