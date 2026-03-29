#!/usr/bin/env python

"""Shared output helpers for agent-facing interfaces."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from crawl4weibo.exceptions.base import CrawlError

DETAIL_LEVEL_COMPACT = "compact"
DETAIL_LEVEL_FULL = "full"
VALID_DETAIL_LEVELS = {DETAIL_LEVEL_COMPACT, DETAIL_LEVEL_FULL}
POST_TEXT_PREVIEW_LIMIT = 220
COMMENT_TEXT_PREVIEW_LIMIT = 180
USER_DESC_PREVIEW_LIMIT = 120


def safe_call(call: Callable[[], Any]) -> Any:
    """Run a callable and convert recoverable exceptions into payloads."""
    try:
        return call()
    except CrawlError as exc:
        return {"error": str(exc), "type": exc.__class__.__name__}
    except Exception as exc:  # pragma: no cover - defensive safeguard
        return {"error": str(exc), "type": exc.__class__.__name__}


def serialize_value(value: Any) -> Any:
    """Convert models and dates into JSON-serializable structures."""
    if hasattr(value, "to_dict"):
        return serialize_value(value.to_dict())
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize_value(item) for item in value]
    return value


def is_error_payload(value: Any) -> bool:
    """Return whether the payload represents a serialized error."""
    return isinstance(value, dict) and "error" in value and "type" in value


def normalize_detail_level(
    detail_level: str | None,
) -> tuple[str, dict[str, str] | None]:
    """Validate and normalize compact/full output settings."""
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


def to_output(
    payload: Any,
    detail_level: str,
    *,
    data_type: str,
) -> Any:
    """Apply compact/full shaping to an already-serialized payload."""
    if is_error_payload(payload) or detail_level == DETAIL_LEVEL_FULL:
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


def format_result(
    result: Any,
    detail_level: str,
    *,
    data_type: str,
    collection_key: str | None = None,
) -> Any:
    """Serialize a result and optionally wrap tuple payloads with pagination."""
    serialized = serialize_value(result)

    if is_error_payload(serialized):
        return serialized

    if collection_key is not None and isinstance(result, tuple):
        items, pagination = serialized
        return {
            collection_key: to_output(items, detail_level, data_type=data_type),
            "pagination": pagination,
        }

    return to_output(serialized, detail_level, data_type=data_type)
