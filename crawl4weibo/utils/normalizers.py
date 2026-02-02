#!/usr/bin/env python

"""
Shared normalization helpers for crawl4weibo
"""

from typing import Any


def parse_label_desc(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            labels.append(item.strip())
            continue
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                labels.append(name.strip())
    return labels
