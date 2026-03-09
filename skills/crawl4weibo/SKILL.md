---
name: crawl4weibo
description: Query Weibo users, posts, and comments through the local crawl4weibo CLI. Use when the workspace contains this repository and the user wants deterministic shell access to the project's Weibo crawling capabilities from OpenClaw.
metadata: {"openclaw":{"homepage":"https://github.com/Praeviso/crawl4weibo","os":["darwin","linux"],"requires":{"bins":["uv"]}}}
---

# crawl4weibo

- Compute the repository root as `repo_root=$(cd "{baseDir}/../.." && pwd)`.
- Treat this as a workspace skill under `<workspace>/skills`; if you move it to `~/.openclaw/skills`, update the repo root calculation first.
- Run all commands from `"$repo_root"` so `uv` can resolve `pyproject.toml`.
- Prefer the built-in CLI instead of ad-hoc Python snippets.
- Commands print JSON to stdout by default.
- Use `--detail full` only when the user asks for full raw fields; otherwise prefer `--detail compact`.
- Add `--cookie`, `--auto-fetch-cookies`, or `--disable-browser-cookies` when login-dependent data is required.
- Add `--no-proxy` when the user explicitly wants to bypass proxies.

## Commands

- Get a user: `cd "$repo_root" && uv run crawl4weibo-cli get-user --uid 2656274875`
- Get user posts: `cd "$repo_root" && uv run crawl4weibo-cli get-user-posts --uid 2656274875 --page 1`
- Get a post: `cd "$repo_root" && uv run crawl4weibo-cli get-post --bid Q6FyDtbQc`
- Search users: `cd "$repo_root" && uv run crawl4weibo-cli search-users --query "雷军" --count 5`
- Search posts: `cd "$repo_root" && uv run crawl4weibo-cli search-posts --query "新能源" --page 1`
- Get comments: `cd "$repo_root" && uv run crawl4weibo-cli get-comments --post-id 1234567890 --page 1`
- Get all comments: `cd "$repo_root" && uv run crawl4weibo-cli get-all-comments --post-id 1234567890 --max-pages 3`
