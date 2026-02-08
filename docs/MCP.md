# MCP Server (for agents)

You can run crawl4weibo as an MCP server so LLM agents can call its tools directly.

## Requirements

- Python 3.10+
- On Python 3.9, the `crawl4weibo[mcp]` extra is unavailable regardless of installer (`uv`, `uvx`, `pip`).

## Install

Recommended (`uv`):

```bash
uv tool install "crawl4weibo[mcp]"
uv tool run --from "crawl4weibo[mcp]" python -m playwright install chromium
```

Alternative (`pip`):

```bash
pip install "crawl4weibo[mcp]"
python -m playwright install chromium
```

## Start Server (stdio)

```bash
crawl4weibo-mcp
```

If the command is not on your `PATH`:

```bash
uv tool run --from "crawl4weibo[mcp]" crawl4weibo-mcp
```

## Available Tools

- `get_user_by_uid`
- `get_user_posts`
- `get_post_by_bid`
- `search_users`
- `search_posts`
- `get_comments`
- `get_all_comments`

## Response Detail Levels

- Default: `detail_level="compact"` for smaller payloads and lower token usage.
- Full: `detail_level="full"` for full model fields (closer to raw API shape).

## CLI Options

- `--cookie`: pass raw cookie string directly. Auto-fetch only applies when `--auto-fetch-cookies` is enabled.
- `--disable-browser-cookies`: use requests-based cookie mode.
- `--auto-fetch-cookies`: auto-fetch cookies on startup (disabled by default).

## MCP Client Config

Claude Desktop:

```json
{
  "mcpServers": {
    "crawl4weibo": {
      "command": "crawl4weibo-mcp",
      "args": ["--auto-fetch-cookies"]
    }
  }
}
```

Codex CLI (recommended `uv tool`):

```bash
uv tool install "crawl4weibo[mcp]"
uv tool run --from "crawl4weibo[mcp]" python -m playwright install chromium
codex mcp add crawl4weibo -- crawl4weibo-mcp --auto-fetch-cookies
```

Codex CLI (`uvx`, prewarm to avoid handshake timeout on first run):

```bash
uvx --from "crawl4weibo[mcp]" python -m playwright install chromium
codex mcp add crawl4weibo -- uvx --from "crawl4weibo[mcp]" \
  crawl4weibo-mcp --auto-fetch-cookies
```
