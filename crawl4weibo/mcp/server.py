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

DETAIL_LEVEL_COMPACT = "compact"
DETAIL_LEVEL_FULL = "full"
VALID_DETAIL_LEVELS = {DETAIL_LEVEL_COMPACT, DETAIL_LEVEL_FULL}
POST_TEXT_PREVIEW_LIMIT = 220
COMMENT_TEXT_PREVIEW_LIMIT = 180
USER_DESC_PREVIEW_LIMIT = 120


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


def _is_error_payload(value: Any) -> bool:
    return isinstance(value, dict) and "error" in value and "type" in value


def _normalize_detail_level(detail_level: str) -> tuple[str, dict[str, str] | None]:
    normalized = (detail_level or DETAIL_LEVEL_COMPACT).strip().lower()
    if normalized in VALID_DETAIL_LEVELS:
        return normalized, None
    return DETAIL_LEVEL_COMPACT, {
        "error": (
            "Invalid detail_level. "
            f"Expected one of: {', '.join(sorted(VALID_DETAIL_LEVELS))}"
        ),
        "type": "ValidationError",
    }


def _truncate_text(value: Any, limit: int) -> tuple[str, bool]:
    if value is None:
        return "", False

    text = str(value)
    compact_text = " ".join(text.split())
    if len(compact_text) <= limit:
        return compact_text, False
    return f"{compact_text[: limit - 3].rstrip()}...", True


def _pick_fields(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in keys:
        if key not in data:
            continue

        value = data[key]
        if value is None or value == "":
            continue

        if isinstance(value, (list, dict, set, tuple)) and len(value) == 0:
            continue

        result[key] = value
    return result


def _compact_user(user: dict[str, Any]) -> dict[str, Any]:
    compact_user = _pick_fields(
        user,
        [
            "id",
            "screen_name",
            "gender",
            "location",
            "followers_count",
            "following_count",
            "posts_count",
            "verified",
            "verified_reason",
            "birthday",
            "education",
            "company",
            "ip_location",
        ],
    )

    description, truncated = _truncate_text(
        user.get("description", ""), USER_DESC_PREVIEW_LIMIT
    )
    if description:
        compact_user["description"] = description
    if truncated:
        compact_user["description_truncated"] = True

    return compact_user


def _compact_comment(comment: dict[str, Any]) -> dict[str, Any]:
    compact_comment = _pick_fields(
        comment,
        [
            "id",
            "created_at",
            "source",
            "user_id",
            "user_screen_name",
            "like_counts",
            "reply_id",
        ],
    )

    text, truncated = _truncate_text(
        comment.get("text", ""), COMMENT_TEXT_PREVIEW_LIMIT
    )
    if text:
        compact_comment["text"] = text
    if truncated:
        compact_comment["text_truncated"] = True

    reply_text, reply_truncated = _truncate_text(
        comment.get("reply_text", ""), COMMENT_TEXT_PREVIEW_LIMIT
    )
    if reply_text:
        compact_comment["reply_text"] = reply_text
    if reply_truncated:
        compact_comment["reply_text_truncated"] = True

    if comment.get("pic_url"):
        compact_comment["has_image"] = True

    return compact_comment


def _compact_post(post: dict[str, Any]) -> dict[str, Any]:
    compact_post = _pick_fields(
        post,
        [
            "id",
            "bid",
            "user_id",
            "created_at",
            "source",
            "reposts_count",
            "comments_count",
            "attitudes_count",
            "is_original",
            "location",
            "topic_ids",
        ],
    )

    text, truncated = _truncate_text(post.get("text", ""), POST_TEXT_PREVIEW_LIMIT)
    if text:
        compact_post["text"] = text
    if truncated:
        compact_post["text_truncated"] = True

    pic_urls = post.get("pic_urls")
    if isinstance(pic_urls, list) and pic_urls:
        compact_post["image_count"] = len(pic_urls)

    if post.get("video_url"):
        compact_post["has_video"] = True

    comments = post.get("comments")
    if isinstance(comments, list) and comments:
        compact_post["comments"] = [_compact_comment(comment) for comment in comments]

    return compact_post


def _to_output(
    payload: Any,
    detail_level: str,
    *,
    data_type: str,
) -> Any:
    if _is_error_payload(payload) or detail_level == DETAIL_LEVEL_FULL:
        return payload

    if data_type == "user" and isinstance(payload, dict):
        return _compact_user(payload)
    if data_type == "users" and isinstance(payload, list):
        return [_compact_user(user) for user in payload]
    if data_type == "post" and isinstance(payload, dict):
        return _compact_post(payload)
    if data_type == "posts" and isinstance(payload, list):
        return [_compact_post(post) for post in payload]
    if data_type == "comments" and isinstance(payload, list):
        return [_compact_comment(comment) for comment in payload]

    return payload


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
    def get_user_by_uid(
        uid: str,
        use_proxy: bool = True,
        detail_level: str = DETAIL_LEVEL_COMPACT,
    ) -> dict[str, Any]:
        detail_level, validation_error = _normalize_detail_level(detail_level)
        if validation_error:
            return validation_error

        result = _safe_call(lambda: client.get_user_by_uid(uid, use_proxy=use_proxy))
        serialized = _serialize_for_mcp(result)
        return _to_output(serialized, detail_level, data_type="user")

    @server.tool()
    def get_user_posts(
        uid: str,
        page: int = 1,
        expand: bool = False,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
        detail_level: str = DETAIL_LEVEL_COMPACT,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        detail_level, validation_error = _normalize_detail_level(detail_level)
        if validation_error:
            return validation_error

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
        serialized = _serialize_for_mcp(result)
        return _to_output(serialized, detail_level, data_type="posts")

    @server.tool()
    def get_post_by_bid(
        bid: str,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
        detail_level: str = DETAIL_LEVEL_COMPACT,
    ) -> dict[str, Any]:
        detail_level, validation_error = _normalize_detail_level(detail_level)
        if validation_error:
            return validation_error

        result = _safe_call(
            lambda: client.get_post_by_bid(
                bid,
                with_comments=with_comments,
                comment_limit=comment_limit,
                use_proxy=use_proxy,
            )
        )
        serialized = _serialize_for_mcp(result)
        return _to_output(serialized, detail_level, data_type="post")

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
        detail_level: str = DETAIL_LEVEL_COMPACT,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        detail_level, validation_error = _normalize_detail_level(detail_level)
        if validation_error:
            return validation_error

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
        serialized = _serialize_for_mcp(result)
        return _to_output(serialized, detail_level, data_type="users")

    @server.tool()
    def search_posts(
        query: str,
        page: int = 1,
        with_comments: bool = False,
        comment_limit: int = 10,
        use_proxy: bool = True,
        detail_level: str = DETAIL_LEVEL_COMPACT,
    ) -> dict[str, Any]:
        detail_level, validation_error = _normalize_detail_level(detail_level)
        if validation_error:
            return validation_error

        result = _safe_call(
            lambda: client.search_posts(
                query,
                page=page,
                with_comments=with_comments,
                comment_limit=comment_limit,
                use_proxy=use_proxy,
            )
        )
        serialized = _serialize_for_mcp(result)

        if _is_error_payload(serialized):
            return serialized

        if isinstance(result, tuple):
            posts, pagination = serialized
            return {
                "posts": _to_output(posts, detail_level, data_type="posts"),
                "pagination": pagination,
            }
        return _to_output(serialized, detail_level, data_type="posts")

    @server.tool()
    def get_comments(
        post_id: str,
        page: int = 1,
        use_proxy: bool = True,
        detail_level: str = DETAIL_LEVEL_COMPACT,
    ) -> dict[str, Any]:
        detail_level, validation_error = _normalize_detail_level(detail_level)
        if validation_error:
            return validation_error

        result = _safe_call(
            lambda: client.get_comments(post_id, page=page, use_proxy=use_proxy)
        )
        serialized = _serialize_for_mcp(result)

        if _is_error_payload(serialized):
            return serialized

        if isinstance(result, tuple):
            comments, pagination = serialized
            return {
                "comments": _to_output(comments, detail_level, data_type="comments"),
                "pagination": pagination,
            }
        return _to_output(serialized, detail_level, data_type="comments")

    @server.tool()
    def get_all_comments(
        post_id: str,
        max_pages: int | None = None,
        use_proxy: bool = True,
        detail_level: str = DETAIL_LEVEL_COMPACT,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        detail_level, validation_error = _normalize_detail_level(detail_level)
        if validation_error:
            return validation_error

        result = _safe_call(
            lambda: client.get_all_comments(
                post_id,
                max_pages=max_pages,
                use_proxy=use_proxy,
            )
        )
        serialized = _serialize_for_mcp(result)
        return _to_output(serialized, detail_level, data_type="comments")

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
