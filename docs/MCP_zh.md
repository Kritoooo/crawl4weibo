# MCP 服务器（供 Agent 调用）

可将 crawl4weibo 作为 MCP 服务运行，供 LLM Agent 直接调用。

## 环境要求

- Python 3.10+
- 在 Python 3.9 下，无论使用 `uv`、`uvx` 还是 `pip`，`crawl4weibo[mcp]` 额外依赖都不会生效。

## 安装

推荐（`uv`）：

```bash
uv tool install "crawl4weibo[mcp]"
uv tool run --from "crawl4weibo[mcp]" python -m playwright install chromium
```

备选（`pip`）：

```bash
pip install "crawl4weibo[mcp]"
python -m playwright install chromium
```

## 启动服务（stdio）

```bash
crawl4weibo-mcp
```

若命令不在 `PATH` 中：

```bash
uv tool run --from "crawl4weibo[mcp]" crawl4weibo-mcp
```

## 提供的工具

- `get_user_by_uid`
- `get_user_posts`
- `get_post_by_bid`
- `search_users`
- `search_posts`
- `get_comments`
- `get_all_comments`

## 响应详细级别

- 默认：`detail_level="compact"`，返回更精简，节省上下文与 token。
- 完整：`detail_level="full"`，返回完整字段（更接近原始 API 结构）。

## CLI 参数

- `--cookie`：直接传入原始 cookie 字符串。仅在启用 `--auto-fetch-cookies` 时才会自动抓取 cookie。
- `--disable-browser-cookies`：禁用 Playwright，改用 requests 方式。
- `--auto-fetch-cookies`：启动时自动抓取 cookie（默认关闭）。

## MCP 客户端配置

Claude Desktop：

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

Codex CLI（推荐 `uv tool`）：

```bash
uv tool install "crawl4weibo[mcp]"
uv tool run --from "crawl4weibo[mcp]" python -m playwright install chromium
codex mcp add crawl4weibo -- crawl4weibo-mcp --auto-fetch-cookies
```

Codex CLI（`uvx`，首次先预热，避免握手超时）：

```bash
uvx --from "crawl4weibo[mcp]" python -m playwright install chromium
codex mcp add crawl4weibo -- uvx --from "crawl4weibo[mcp]" \
  crawl4weibo-mcp --auto-fetch-cookies
```
