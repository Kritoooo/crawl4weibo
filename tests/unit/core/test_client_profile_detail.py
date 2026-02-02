"""Tests for WeiboClient profile detail enrichment"""

from unittest.mock import patch

import pytest

from crawl4weibo.utils.cookie_fetcher import LOGIN_COOKIE_NAMES


@pytest.mark.unit
class TestWeiboClientProfileDetail:
    def test_has_login_cookies_detects_cookie(self, client_no_rate_limit):
        client = client_no_rate_limit
        assert client._has_login_cookies() is False

        cookie_name = next(iter(LOGIN_COOKIE_NAMES))
        client.session.cookies.set(cookie_name, "test")
        assert client._has_login_cookies() is True

    def test_merge_user_info_prefers_non_empty(self, client_no_rate_limit):
        client = client_no_rate_limit
        base = {
            "screen_name": "Base",
            "description": "Base description",
            "empty_str": "",
            "empty_list": [],
            "zero_count": 0,
            "flag": False,
        }
        extra = {
            "screen_name": "Override",
            "description": "",
            "empty_str": "Filled",
            "empty_list": ["item"],
            "zero_count": 12,
            "flag": True,
            "new_field": "New",
            "skip_empty": "",
        }

        merged = client._merge_user_info(base, extra)

        assert merged["screen_name"] == "Base"
        assert merged["description"] == "Base description"
        assert merged["empty_str"] == "Filled"
        assert merged["empty_list"] == ["item"]
        assert merged["zero_count"] == 12
        assert merged["flag"] is True
        assert merged["new_field"] == "New"
        assert "skip_empty" not in merged

    def test_get_user_by_uid_enriches_with_profile_detail(self, client_no_rate_limit):
        client = client_no_rate_limit
        user_response = {
            "data": {
                "userInfo": {
                    "id": 123,
                    "screen_name": "BaseUser",
                    "followers_count": 0,
                    "follow_count": 5,
                    "statuses_count": 9,
                    "description": "Base description",
                    "gender": "m",
                    "profile_image_url": "http://avatar.test",
                }
            }
        }
        detail_response = {
            "data": {
                "ip_location": "IP location: UK",
                "real_auth": True,
                "label_desc": ["Label A", {"name": "Label B"}],
                "followers": {"total_number": 120},
                "description": "",
            }
        }

        with (
            patch.object(client, "_has_login_cookies", return_value=True),
            patch.object(
                client,
                "_request",
                side_effect=[user_response, detail_response],
            ),
        ):
            user = client.get_user_by_uid("123")

        assert user.ip_location == "IP location: UK"
        assert user.real_auth is True
        assert user.label_desc == ["Label A", "Label B"]
        assert user.followers_count == 120
        assert user.description == "Base description"
