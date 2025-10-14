"""Tests for WeiboClient"""

import pytest

from crawl4weibo import Post, User, WeiboClient


@pytest.mark.unit
class TestWeiboClient:
    def test_client_initialization(self):
        """Test client initialization"""
        client = WeiboClient()
        assert client is not None
        assert hasattr(client, "get_user_by_uid")
        assert hasattr(client, "get_user_posts")
        assert hasattr(client, "get_post_by_bid")
        assert hasattr(client, "search_users")
        assert hasattr(client, "search_posts")

    def test_client_methods_exist(self):
        """Test that all expected methods exist"""
        client = WeiboClient()
        methods = [
            "get_user_by_uid",
            "get_user_posts",
            "get_post_by_bid",
            "search_users",
            "search_posts",
        ]

        for method in methods:
            assert hasattr(client, method), f"Method {method} should exist"
            assert callable(getattr(client, method)), (
                f"Method {method} should be callable"
            )

    def test_imports_work(self):
        """Test that imports work correctly"""
        assert WeiboClient is not None
        assert User is not None
        assert Post is not None
