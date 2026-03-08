#!/usr/bin/env python

"""Command line interface for crawl4weibo."""

from __future__ import annotations

import argparse
import json
from typing import Any

from crawl4weibo.core.client import WeiboClient
from crawl4weibo.utils.agent_output import (
    DETAIL_LEVEL_COMPACT,
    format_result,
    is_error_payload,
    normalize_detail_level,
    safe_call,
)


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


def _add_client_args(parser: argparse.ArgumentParser) -> None:
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
            "Useful when login-dependent data is required."
        ),
    )


def _add_request_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Disable proxy usage for this request.",
    )
    parser.add_argument(
        "--detail",
        "--detail-level",
        dest="detail_level",
        default=DETAIL_LEVEL_COMPACT,
        help="Response detail level: compact or full.",
    )


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _handle_get_user(
    client: WeiboClient,
    args: argparse.Namespace,
    detail_level: str,
) -> Any:
    result = safe_call(
        lambda: client.get_user_by_uid(args.uid, use_proxy=not args.no_proxy)
    )
    return format_result(result, detail_level, data_type="user")


def _handle_get_user_posts(
    client: WeiboClient,
    args: argparse.Namespace,
    detail_level: str,
) -> Any:
    result = safe_call(
        lambda: client.get_user_posts(
            args.uid,
            page=args.page,
            expand=args.expand,
            with_comments=args.with_comments,
            comment_limit=args.comment_limit,
            use_proxy=not args.no_proxy,
        )
    )
    return format_result(result, detail_level, data_type="posts")


def _handle_get_post(
    client: WeiboClient,
    args: argparse.Namespace,
    detail_level: str,
) -> Any:
    result = safe_call(
        lambda: client.get_post_by_bid(
            args.bid,
            with_comments=args.with_comments,
            comment_limit=args.comment_limit,
            use_proxy=not args.no_proxy,
        )
    )
    return format_result(result, detail_level, data_type="post")


def _handle_search_users(
    client: WeiboClient,
    args: argparse.Namespace,
    detail_level: str,
) -> Any:
    age_range: tuple[int | None, int | None] | None = None
    if args.min_age is not None or args.max_age is not None:
        age_range = (args.min_age, args.max_age)

    result = safe_call(
        lambda: client.search_users(
            args.query,
            page=args.page,
            count=args.count,
            use_proxy=not args.no_proxy,
            gender=args.gender,
            location=args.location,
            birthday=args.birthday,
            age_range=age_range,
            education=args.education,
            company=args.company,
        )
    )
    return format_result(result, detail_level, data_type="users")


def _handle_search_posts(
    client: WeiboClient,
    args: argparse.Namespace,
    detail_level: str,
) -> Any:
    result = safe_call(
        lambda: client.search_posts(
            args.query,
            page=args.page,
            with_comments=args.with_comments,
            comment_limit=args.comment_limit,
            use_proxy=not args.no_proxy,
        )
    )
    return format_result(
        result,
        detail_level,
        data_type="posts",
        collection_key="posts",
    )


def _handle_get_comments(
    client: WeiboClient,
    args: argparse.Namespace,
    detail_level: str,
) -> Any:
    result = safe_call(
        lambda: client.get_comments(
            args.post_id,
            page=args.page,
            use_proxy=not args.no_proxy,
        )
    )
    return format_result(
        result,
        detail_level,
        data_type="comments",
        collection_key="comments",
    )


def _handle_get_all_comments(
    client: WeiboClient,
    args: argparse.Namespace,
    detail_level: str,
) -> Any:
    result = safe_call(
        lambda: client.get_all_comments(
            args.post_id,
            max_pages=args.max_pages,
            use_proxy=not args.no_proxy,
        )
    )
    return format_result(result, detail_level, data_type="comments")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run crawl4weibo CLI commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_user_parser = subparsers.add_parser(
        "get-user",
        help="Fetch a user profile by UID.",
    )
    _add_client_args(get_user_parser)
    _add_request_args(get_user_parser)
    get_user_parser.add_argument("--uid", required=True, help="Weibo user UID.")
    get_user_parser.set_defaults(handler=_handle_get_user)

    get_user_posts_parser = subparsers.add_parser(
        "get-user-posts",
        help="Fetch a user's posts by UID.",
    )
    _add_client_args(get_user_posts_parser)
    _add_request_args(get_user_posts_parser)
    get_user_posts_parser.add_argument(
        "--uid", required=True, help="Weibo user UID."
    )
    get_user_posts_parser.add_argument(
        "--page", type=int, default=1, help="Timeline page number."
    )
    get_user_posts_parser.add_argument(
        "--expand",
        action="store_true",
        help="Expand long-text posts when available.",
    )
    get_user_posts_parser.add_argument(
        "--with-comments",
        action="store_true",
        help="Fetch comments for each returned post.",
    )
    get_user_posts_parser.add_argument(
        "--comment-limit",
        type=int,
        default=10,
        help="Maximum comments per post when --with-comments is enabled.",
    )
    get_user_posts_parser.set_defaults(handler=_handle_get_user_posts)

    get_post_parser = subparsers.add_parser(
        "get-post",
        help="Fetch a single post by BID.",
    )
    _add_client_args(get_post_parser)
    _add_request_args(get_post_parser)
    get_post_parser.add_argument("--bid", required=True, help="Weibo post BID.")
    get_post_parser.add_argument(
        "--with-comments",
        action="store_true",
        help="Fetch comments for the post.",
    )
    get_post_parser.add_argument(
        "--comment-limit",
        type=int,
        default=10,
        help="Maximum comments when --with-comments is enabled.",
    )
    get_post_parser.set_defaults(handler=_handle_get_post)

    search_users_parser = subparsers.add_parser(
        "search-users",
        help="Search Weibo users by keyword.",
    )
    _add_client_args(search_users_parser)
    _add_request_args(search_users_parser)
    search_users_parser.add_argument(
        "--query", required=True, help="Search keyword."
    )
    search_users_parser.add_argument(
        "--page", type=int, default=1, help="Search results page number."
    )
    search_users_parser.add_argument(
        "--count", type=int, default=10, help="Number of results per page."
    )
    search_users_parser.add_argument("--gender", help="Gender filter.")
    search_users_parser.add_argument("--location", help="Location filter.")
    search_users_parser.add_argument("--birthday", help="Birthday filter.")
    search_users_parser.add_argument("--min-age", type=int, help="Minimum age.")
    search_users_parser.add_argument("--max-age", type=int, help="Maximum age.")
    search_users_parser.add_argument("--education", help="Education filter.")
    search_users_parser.add_argument("--company", help="Company filter.")
    search_users_parser.set_defaults(handler=_handle_search_users)

    search_posts_parser = subparsers.add_parser(
        "search-posts",
        help="Search Weibo posts by keyword.",
    )
    _add_client_args(search_posts_parser)
    _add_request_args(search_posts_parser)
    search_posts_parser.add_argument(
        "--query", required=True, help="Search keyword."
    )
    search_posts_parser.add_argument(
        "--page", type=int, default=1, help="Search results page number."
    )
    search_posts_parser.add_argument(
        "--with-comments",
        action="store_true",
        help="Fetch comments for each returned post.",
    )
    search_posts_parser.add_argument(
        "--comment-limit",
        type=int,
        default=10,
        help="Maximum comments per post when --with-comments is enabled.",
    )
    search_posts_parser.set_defaults(handler=_handle_search_posts)

    get_comments_parser = subparsers.add_parser(
        "get-comments",
        help="Fetch a page of comments for a post.",
    )
    _add_client_args(get_comments_parser)
    _add_request_args(get_comments_parser)
    get_comments_parser.add_argument(
        "--post-id", required=True, help="Numeric Weibo post ID."
    )
    get_comments_parser.add_argument(
        "--page", type=int, default=1, help="Comment page number."
    )
    get_comments_parser.set_defaults(handler=_handle_get_comments)

    get_all_comments_parser = subparsers.add_parser(
        "get-all-comments",
        help="Fetch all comments for a post with optional max pages.",
    )
    _add_client_args(get_all_comments_parser)
    _add_request_args(get_all_comments_parser)
    get_all_comments_parser.add_argument(
        "--post-id", required=True, help="Numeric Weibo post ID."
    )
    get_all_comments_parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to fetch before stopping.",
    )
    get_all_comments_parser.set_defaults(handler=_handle_get_all_comments)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    detail_level, validation_error = normalize_detail_level(args.detail_level)
    if validation_error:
        _print_json(validation_error)
        return 2

    try:
        client = _build_client(
            cookie=args.cookie,
            use_browser_cookies=not args.disable_browser_cookies,
            auto_fetch_cookies=args.auto_fetch_cookies,
        )
        payload = args.handler(client, args, detail_level)
    except Exception as exc:  # pragma: no cover - defensive safeguard
        payload = {"error": str(exc), "type": exc.__class__.__name__}

    _print_json(payload)
    return 1 if is_error_payload(payload) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
