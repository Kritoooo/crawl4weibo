#!/usr/bin/env python

"""MCP server entrypoint for crawl4weibo.

This module keeps the MCP dependency optional. If users install with
`pip install "crawl4weibo[mcp]"`, they can run:

    crawl4weibo-mcp
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from typing import Any, Callable

from crawl4weibo.core.client import WeiboClient
from crawl4weibo.exceptions.base import CrawlError


def _build_client(
    cookie: str | None,
    use_browser_cookies: bool,
    auto_fetch_cookies: bool,
) -> WeiboClient:
    return WeiboClient(
        cookies=cookie,
        auto_fetch_cookies=auto_fetch_cookies and cookie is None,
        use_browser_cookies=use_browser_cookies,
        log_level="ERROR",
    )


def _safe_call(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except CrawlError as exc:
        return {"error": str(exc), "type": exc.__class__.__name__}
    except Exception as exc:  # pragma: no cover - defensive safeguard
        return {"error": str(exc), "type": exc.__class__.__name__}


def _serialize_for_mcp(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _serialize_for_mcp(value.to_dict())
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _serialize_for_mcp(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_for_mcp(item) for item in value]
    return value


def create_mcp_server(
    *,
    cookie: str | None = None,
    use_browser_cookies: bool = True,
    auto_fetch_cookies: bool = False,
):
    """Create and configure MCP server instance."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised in tests via monkeypatch
        raise RuntimeError(
            "MCP support is not installed. Install with: pip install 'crawl4weibo[mcp]'"
        ) from exc

    client = _build_client(
        cookie=cookie,
        use_browser_cookies=use_browser_cookies,
        auto_fetch_cookies=auto_fetch_cookies,
    )

    server = FastMCP("crawl4weibo")

    @server.tool()
    def get_user_by_uid(uid: str, use_proxy: bool = True) -> dict[str, Any]:
        result = _safe_call(lambda: client.get_user_by_uid(uid, use_proxy=use_proxy))
        return _serialize_for_mcp(result)

    @server.tool()
    def get_user_posts(
        uid: str,
        page: int = 1,
        expand: bool = False,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        result = _safe_call(
            lambda: client.get_user_posts(
                uid,
                page=page,
                expand=expand,
                with_comments=with_comments,
                comment_limit=comment_limit,
                use_proxy=use_proxy,
            )
        )
        return _serialize_for_mcp(result)

    @server.tool()
    def get_post_by_bid(
        bid: str,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> dict[str, Any]:
        result = _safe_call(
            lambda: client.get_post_by_bid(
                bid,
                with_comments=with_comments,
                comment_limit=comment_limit,
                use_proxy=use_proxy,
            )
        )
        return _serialize_for_mcp(result)

    @server.tool()
    def search_users(
        query: str,
        page: int = 1,
        count: int = 10,
        use_proxy: bool = True,
        gender: str | None = None,
        location: str | None = None,
        birthday: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        education: str | None = None,
        company: str | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        age_range: tuple[int | None, int | None] | None = None
        if min_age is not None or max_age is not None:
            age_range = (min_age, max_age)

        result = _safe_call(
            lambda: client.search_users(
                query,
                page=page,
                count=count,
                use_proxy=use_proxy,
                gender=gender,
                location=location,
                birthday=birthday,
                age_range=age_range,
                education=education,
                company=company,
            )
        )
        return _serialize_for_mcp(result)

    @server.tool()
    def search_posts(
        query: str,
        page: int = 1,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
    ) -> dict[str, Any]:
        result = _safe_call(
            lambda: client.search_posts(
                query,
                page=page,
                with_comments=with_comments,
                comment_limit=comment_limit,
                use_proxy=use_proxy,
            )
        )
        if isinstance(result, tuple):
            posts, pagination = result
            return {
                "posts": _serialize_for_mcp(posts),
                "pagination": _serialize_for_mcp(pagination),
            }
        return _serialize_for_mcp(result)

    @server.tool()
    def get_comments(
        post_id: str,
        page: int = 1,
        use_proxy: bool = True,
    ) -> dict[str, Any]:
        result = _safe_call(
            lambda: client.get_comments(post_id, page=page, use_proxy=use_proxy)
        )
        if isinstance(result, tuple):
            comments, pagination = result
            return {
                "comments": _serialize_for_mcp(comments),
                "pagination": _serialize_for_mcp(pagination),
            }
        return _serialize_for_mcp(result)

    @server.tool()
    def get_all_comments(
        post_id: str,
        max_pages: int | None = None,
        use_proxy: bool = True,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        result = _safe_call(
            lambda: client.get_all_comments(
                post_id,
                max_pages=max_pages,
                use_proxy=use_proxy,
            )
        )
        return _serialize_for_mcp(result)

    @server.resource("weibo://health")
    def health() -> str:
        return json.dumps({"status": "ok", "service": "crawl4weibo-mcp"})

    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run crawl4weibo MCP server")
    parser.add_argument(
        "--cookie",
        default=None,
        help=(
            "Optional raw cookie string. Auto fetch only runs when "
            "--auto-fetch-cookies is enabled."
        ),
    )
    parser.add_argument(
        "--disable-browser-cookies",
        action="store_true",
        help="Disable Playwright browser cookie fetch and use requests mode instead.",
    )
    parser.add_argument(
        "--auto-fetch-cookies",
        action="store_true",
        help=(
            "Enable automatic cookie fetching during startup. "
            "Disabled by default for MCP to avoid interactive startup."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    try:
        server = create_mcp_server(
            cookie=args.cookie,
            use_browser_cookies=not args.disable_browser_cookies,
            auto_fetch_cookies=args.auto_fetch_cookies,
        )
        server.run()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":  # pragma: no cover
    main()
