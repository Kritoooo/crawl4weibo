"""Tests for crawl4weibo MCP server integration."""

import importlib
import sys
from datetime import date
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from crawl4weibo.exceptions.base import CrawlError


class FakeFastMCP:
    """Minimal test double for FastMCP."""

    def __init__(self, name: str):
        self.name = name
        self.tools: dict[str, object] = {}
        self.resources: dict[str, object] = {}
        self.run_calls = 0

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator

    def resource(self, uri: str):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator

    def run(self):
        self.run_calls += 1


@pytest.fixture
def fake_mcp_module(monkeypatch):
    """Inject a fake mcp.server.fastmcp module for tests."""
    mcp_module = ModuleType("mcp")
    server_module = ModuleType("mcp.server")
    fastmcp_module = ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeFastMCP

    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)

    mcp_module.server = server_module
    server_module.fastmcp = fastmcp_module

    yield

    for module_name in ["crawl4weibo.mcp.server", "crawl4weibo.mcp", "crawl4weibo"]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)


@pytest.fixture
def server_module(fake_mcp_module):
    """Reload module after fake MCP injection."""
    module = importlib.import_module("crawl4weibo.mcp.server")
    return importlib.reload(module)


@pytest.mark.unit
def test_create_mcp_server_registers_tools_and_resource(server_module):
    with patch.object(server_module, "_build_client", return_value=MagicMock()):
        server = server_module.create_mcp_server()

    expected_tools = {
        "get_user_by_uid",
        "get_user_posts",
        "get_post_by_bid",
        "search_users",
        "search_posts",
        "get_comments",
        "get_all_comments",
    }

    assert set(server.tools) == expected_tools
    assert "weibo://health" in server.resources


@pytest.mark.unit
def test_get_user_by_uid_tool_serializes_result(server_module):
    mock_client = MagicMock()
    mock_user = MagicMock()
    mock_user.to_dict.return_value = {"id": "1", "screen_name": "Alice"}
    mock_client.get_user_by_uid.return_value = mock_user

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    result = server.tools["get_user_by_uid"]("1")

    assert result == {"id": "1", "screen_name": "Alice"}
    mock_client.get_user_by_uid.assert_called_once_with("1", use_proxy=True)


@pytest.mark.unit
def test_get_user_posts_tool_passes_arguments(server_module):
    mock_client = MagicMock()
    mock_post = MagicMock()
    mock_post.to_dict.return_value = {"id": "10", "text": "post"}
    mock_client.get_user_posts.return_value = [mock_post]

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    result = server.tools["get_user_posts"](
        "123",
        page=2,
        expand=True,
        with_comments=True,
        comment_limit=5,
        use_proxy=False,
    )

    assert result == [{"id": "10", "text": "post"}]
    mock_client.get_user_posts.assert_called_once_with(
        "123",
        page=2,
        expand=True,
        with_comments=True,
        comment_limit=5,
        use_proxy=False,
    )


@pytest.mark.unit
def test_get_user_posts_compact_mode_reduces_payload(server_module):
    mock_client = MagicMock()
    mock_post = MagicMock()
    mock_post.to_dict.return_value = {
        "id": "10",
        "bid": "abc",
        "user_id": "u1",
        "text": "x" * 300,
        "pic_urls": ["a", "b", "c"],
        "video_url": "https://video.example.com/v.mp4",
        "created_at": "2026-02-08T16:00:00+08:00",
        "comments_count": 3,
        "attitudes_count": 9,
    }
    mock_client.get_user_posts.return_value = [mock_post]

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    compact_result = server.tools["get_user_posts"]("123")
    full_result = server.tools["get_user_posts"]("123", detail_level="full")

    assert compact_result[0]["id"] == "10"
    assert compact_result[0]["text_truncated"] is True
    assert compact_result[0]["image_count"] == 3
    assert compact_result[0]["has_video"] is True
    assert "video_url" not in compact_result[0]

    assert full_result[0]["video_url"] == "https://video.example.com/v.mp4"
    assert full_result[0]["pic_urls"] == ["a", "b", "c"]


@pytest.mark.unit
def test_search_posts_tool_returns_posts_and_pagination(server_module):
    mock_client = MagicMock()

    post = MagicMock()
    post.to_dict.return_value = {"id": "100", "text": "hello"}
    mock_client.search_posts.return_value = ([post], {"page": 2, "has_more": True})

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    result = server.tools["search_posts"]("python")

    assert result["posts"] == [{"id": "100", "text": "hello"}]
    assert result["pagination"] == {"page": 2, "has_more": True}


@pytest.mark.unit
def test_search_posts_tool_non_tuple_result_is_returned(server_module):
    mock_client = MagicMock()
    mock_client.search_posts.return_value = {"error": "blocked"}

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    result = server.tools["search_posts"]("python")
    assert result == {"error": "blocked"}


@pytest.mark.unit
def test_search_users_maps_min_max_age_to_age_range(server_module):
    mock_client = MagicMock()
    mock_client.search_users.return_value = []

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    server.tools["search_users"]("bob", min_age=20, max_age=30)

    call_kwargs = mock_client.search_users.call_args.kwargs
    assert call_kwargs["age_range"] == (20, 30)


@pytest.mark.unit
def test_tool_returns_error_payload_on_exception(server_module):
    mock_client = MagicMock()
    mock_client.get_post_by_bid.side_effect = RuntimeError("boom")

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    result = server.tools["get_post_by_bid"]("abc")

    assert result["error"] == "boom"
    assert result["type"] == "RuntimeError"


@pytest.mark.unit
def test_get_comments_and_get_all_comments_tools(server_module):
    mock_client = MagicMock()

    comment = MagicMock()
    comment.to_dict.return_value = {"id": "c1", "text": "nice"}
    mock_client.get_comments.return_value = ([comment], {"page": 1, "max": 3})
    mock_client.get_all_comments.return_value = [comment]

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    comments_result = server.tools["get_comments"]("999", page=2, use_proxy=False)
    all_comments_result = server.tools["get_all_comments"](
        "999",
        max_pages=4,
        use_proxy=False,
    )

    assert comments_result == {
        "comments": [{"id": "c1", "text": "nice"}],
        "pagination": {"page": 1, "max": 3},
    }
    assert all_comments_result == [{"id": "c1", "text": "nice"}]

    mock_client.get_comments.assert_called_once_with("999", page=2, use_proxy=False)
    mock_client.get_all_comments.assert_called_once_with(
        "999",
        max_pages=4,
        use_proxy=False,
    )


@pytest.mark.unit
def test_get_comments_compact_mode_reduces_payload(server_module):
    mock_client = MagicMock()
    comment = MagicMock()
    comment.to_dict.return_value = {
        "id": "c1",
        "text": "nice " * 80,
        "created_at": "1小时前",
        "source": "来自北京",
        "user_id": "u1",
        "user_screen_name": "Alice",
        "user_avatar_url": "https://avatar.example.com/a.jpg",
        "user_verified": False,
        "user_verified_type": -1,
        "like_counts": 3,
        "reply_id": "r1",
        "reply_text": "reply " * 80,
        "pic_url": "https://img.example.com/p.jpg",
    }

    mock_client.get_comments.return_value = ([comment], {"total_number": 1, "max": 1})

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    compact_result = server.tools["get_comments"]("999")
    full_result = server.tools["get_comments"]("999", detail_level="full")

    compact_comment = compact_result["comments"][0]
    assert compact_comment["id"] == "c1"
    assert compact_comment["text_truncated"] is True
    assert compact_comment["reply_text_truncated"] is True
    assert compact_comment["has_image"] is True
    assert "user_avatar_url" not in compact_comment

    full_comment = full_result["comments"][0]
    assert full_comment["user_avatar_url"] == "https://avatar.example.com/a.jpg"
    assert full_comment["pic_url"] == "https://img.example.com/p.jpg"


@pytest.mark.unit
def test_get_user_by_uid_compact_mode_reduces_payload(server_module):
    mock_client = MagicMock()
    mock_user = MagicMock()
    mock_user.to_dict.return_value = {
        "id": "u1",
        "screen_name": "Alice",
        "description": "desc " * 100,
        "followers_count": 123,
        "avatar_url": "https://avatar.example.com/a.jpg",
        "verified": True,
    }
    mock_client.get_user_by_uid.return_value = mock_user

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    compact_result = server.tools["get_user_by_uid"]("u1")
    full_result = server.tools["get_user_by_uid"]("u1", detail_level="full")

    assert compact_result["id"] == "u1"
    assert compact_result["description_truncated"] is True
    assert "avatar_url" not in compact_result

    assert full_result["avatar_url"] == "https://avatar.example.com/a.jpg"


@pytest.mark.unit
def test_invalid_detail_level_returns_validation_error(server_module):
    mock_client = MagicMock()

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    result = server.tools["search_posts"]("ai", detail_level="verbose")

    assert result["type"] == "ValidationError"
    assert "detail_level" in result["error"]
    mock_client.search_posts.assert_not_called()


@pytest.mark.unit
def test_get_comments_non_tuple_result_is_returned(server_module):
    mock_client = MagicMock()
    mock_client.get_comments.return_value = {"error": "timeout"}

    with patch.object(server_module, "_build_client", return_value=mock_client):
        server = server_module.create_mcp_server()

    result = server.tools["get_comments"]("999")
    assert result == {"error": "timeout"}


@pytest.mark.unit
def test_health_resource_returns_json(server_module):
    with patch.object(server_module, "_build_client", return_value=MagicMock()):
        server = server_module.create_mcp_server()

    payload = server.resources["weibo://health"]()
    assert payload == '{"status": "ok", "service": "crawl4weibo-mcp"}'


@pytest.mark.unit
def test_parse_args_defaults_and_flags(server_module):
    defaults = server_module.parse_args([])
    assert defaults.cookie is None
    assert defaults.disable_browser_cookies is False
    assert defaults.auto_fetch_cookies is False

    flags = server_module.parse_args(
        [
            "--cookie",
            "SUB=abc",
            "--disable-browser-cookies",
            "--auto-fetch-cookies",
        ]
    )
    assert flags.cookie == "SUB=abc"
    assert flags.disable_browser_cookies is True
    assert flags.auto_fetch_cookies is True


@pytest.mark.unit
def test_safe_call_handles_crawl_error_and_serialize_date(server_module):
    result = server_module._safe_call(lambda: (_ for _ in ()).throw(CrawlError("x")))
    assert result == {"error": "x", "type": "CrawlError"}

    serialized = server_module._serialize_for_mcp({"day": date(2026, 2, 8)})
    assert serialized == {"day": "2026-02-08"}


@pytest.mark.unit
def test_build_client_passes_expected_constructor_arguments(server_module):
    with patch.object(server_module, "WeiboClient") as mock_cls:
        server_module._build_client(
            cookie="SUB=token",
            use_browser_cookies=False,
            auto_fetch_cookies=True,
        )

    mock_cls.assert_called_once_with(
        cookies="SUB=token",
        auto_fetch_cookies=False,
        use_browser_cookies=False,
        log_level="ERROR",
    )


@pytest.mark.unit
def test_parse_args_cookie_help_mentions_auto_fetch_flag(server_module):
    parser = server_module.argparse.ArgumentParser(
        description="Run crawl4weibo MCP server"
    )
    parser.add_argument(
        "--cookie",
        default=None,
        help=(
            "Optional raw cookie string. Auto fetch only runs when "
            "--auto-fetch-cookies is enabled."
        ),
    )

    help_text = parser.format_help()
    assert "--auto-fetch-cookies is enabled" in help_text


@pytest.mark.unit
def test_top_level_module_skips_mcp_export_on_py39(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 9, 18))

    for module_name in ["crawl4weibo", "crawl4weibo.mcp", "crawl4weibo.mcp.server"]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    module = importlib.import_module("crawl4weibo")
    module = importlib.reload(module)

    assert "create_mcp_server" not in module.__all__


@pytest.mark.unit
def test_main_runs_server_with_expected_flags(server_module):
    fake_server = FakeFastMCP("crawl4weibo")

    with patch.object(server_module, "parse_args") as mock_parse, patch.object(
        server_module,
        "create_mcp_server",
        return_value=fake_server,
    ) as mock_create:
        mock_parse.return_value = server_module.argparse.Namespace(
            cookie="SUB=test",
            disable_browser_cookies=True,
            auto_fetch_cookies=True,
        )

        server_module.main([])

    assert fake_server.run_calls == 1
    mock_create.assert_called_once_with(
        cookie="SUB=test",
        use_browser_cookies=False,
        auto_fetch_cookies=True,
    )


@pytest.mark.unit
def test_main_exits_with_message_when_server_creation_fails(server_module):
    with patch.object(server_module, "parse_args") as mock_parse, patch.object(
        server_module,
        "create_mcp_server",
        side_effect=RuntimeError("install mcp"),
    ):
        mock_parse.return_value = server_module.argparse.Namespace(
            cookie=None,
            disable_browser_cookies=False,
            auto_fetch_cookies=False,
        )

        with pytest.raises(SystemExit, match="install mcp"):
            server_module.main([])


@pytest.mark.unit
def test_create_mcp_server_raises_runtime_error_without_mcp(monkeypatch):
    for module_name in [
        "crawl4weibo.mcp.server",
        "mcp.server.fastmcp",
        "mcp.server",
        "mcp",
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "mcp.server.fastmcp":
            raise ImportError("mcp not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    module = importlib.import_module("crawl4weibo.mcp.server")
    module = importlib.reload(module)

    with patch.object(module, "_build_client", return_value=MagicMock()), pytest.raises(
        RuntimeError,
        match="MCP support is not installed",
    ):
        module.create_mcp_server()
