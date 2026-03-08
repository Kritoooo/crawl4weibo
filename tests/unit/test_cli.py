"""Tests for the crawl4weibo CLI."""

import json
from unittest.mock import MagicMock, patch

import pytest

import crawl4weibo.cli as cli


@pytest.mark.unit
def test_parse_args_defaults_for_get_user_command():
    args = cli.parse_args(["get-user", "--uid", "1"])

    assert args.command == "get-user"
    assert args.uid == "1"
    assert args.cookie is None
    assert args.disable_browser_cookies is False
    assert args.auto_fetch_cookies is False
    assert args.no_proxy is False
    assert args.detail_level == "compact"


@pytest.mark.unit
def test_get_user_command_outputs_compact_json(capsys):
    mock_client = MagicMock()
    mock_user = MagicMock()
    mock_user.to_dict.return_value = {
        "id": "u1",
        "screen_name": "Alice",
        "description": "desc " * 100,
        "avatar_url": "https://avatar.example.com/a.jpg",
        "followers_count": 123,
    }
    mock_client.get_user_by_uid.return_value = mock_user

    with patch.object(cli, "_build_client", return_value=mock_client):
        exit_code = cli.main(["get-user", "--uid", "u1"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["id"] == "u1"
    assert payload["description_truncated"] is True
    assert "avatar_url" not in payload
    mock_client.get_user_by_uid.assert_called_once_with("u1", use_proxy=True)


@pytest.mark.unit
def test_get_user_command_supports_full_detail(capsys):
    mock_client = MagicMock()
    mock_user = MagicMock()
    mock_user.to_dict.return_value = {
        "id": "u1",
        "screen_name": "Alice",
        "avatar_url": "https://avatar.example.com/a.jpg",
    }
    mock_client.get_user_by_uid.return_value = mock_user

    with patch.object(cli, "_build_client", return_value=mock_client):
        exit_code = cli.main(["get-user", "--uid", "u1", "--detail", "full"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["avatar_url"] == "https://avatar.example.com/a.jpg"


@pytest.mark.unit
def test_search_posts_command_wraps_pagination(capsys):
    mock_client = MagicMock()
    mock_post = MagicMock()
    mock_post.to_dict.return_value = {
        "id": "p1",
        "text": "hello",
        "pic_urls": ["a", "b"],
    }
    mock_client.search_posts.return_value = ([mock_post], {"page": 2, "has_more": True})

    with patch.object(cli, "_build_client", return_value=mock_client):
        exit_code = cli.main(["search-posts", "--query", "python"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["pagination"] == {"page": 2, "has_more": True}
    assert payload["posts"][0]["image_count"] == 2


@pytest.mark.unit
def test_cli_returns_error_payload_and_nonzero_exit(capsys):
    mock_client = MagicMock()
    mock_client.get_post_by_bid.side_effect = RuntimeError("boom")

    with patch.object(cli, "_build_client", return_value=mock_client):
        exit_code = cli.main(["get-post", "--bid", "abc"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload == {"error": "boom", "type": "RuntimeError"}


@pytest.mark.unit
def test_cli_rejects_invalid_detail_level_before_building_client(capsys):
    with patch.object(cli, "_build_client") as mock_build_client:
        exit_code = cli.main(["get-user", "--uid", "u1", "--detail", "verbose"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["type"] == "ValidationError"
    mock_build_client.assert_not_called()


@pytest.mark.unit
def test_search_users_command_passes_client_flags_and_filters(capsys):
    mock_client = MagicMock()
    mock_client.search_users.return_value = []

    with patch.object(cli, "_build_client", return_value=mock_client) as mock_build:
        exit_code = cli.main(
            [
                "search-users",
                "--query",
                "alice",
                "--cookie",
                "SUB=abc",
                "--disable-browser-cookies",
                "--auto-fetch-cookies",
                "--min-age",
                "20",
                "--max-age",
                "30",
                "--no-proxy",
            ]
        )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == []

    mock_build.assert_called_once_with(
        cookie="SUB=abc",
        use_browser_cookies=False,
        auto_fetch_cookies=True,
    )
    mock_client.search_users.assert_called_once_with(
        "alice",
        page=1,
        count=10,
        use_proxy=False,
        gender=None,
        location=None,
        birthday=None,
        age_range=(20, 30),
        education=None,
        company=None,
    )
