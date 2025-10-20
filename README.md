# Crawl4Weibo

Crawl4Weibo 是一个开箱即用的微博爬虫 Python 库，模拟移动端请求、处理常见反爬策略，并返回结构化数据模型，适合数据采集、分析与监控场景。

## ✨ 特性
- 无需 Cookie 即可运行，自动初始化 session 和移动端 UA。
- 内置 432 防护处理与指数退避重试，减少请求失败。
- 标准化的 `User` 与 `Post` 数据模型，可递归访问转发内容。
- 支持微博长文展开、关键词搜索、用户列表抓取与批量分页。
- 提供图像下载工具，支持单条、批量和整页下载，并带重复文件检查。
- 统一日志与错误类型，便于快速定位网络、解析或鉴权问题。

## 安装
```bash
pip install crawl4weibo
```
或使用更快的 `uv`：
```bash
uv pip install crawl4weibo
```

## 快速开始
```python
from crawl4weibo import WeiboClient

client = WeiboClient()
uid = "2656274875"

user = client.get_user_by_uid(uid)
print(user.screen_name, user.followers_count)

posts = client.get_user_posts(uid, page=1, expand=True)
for post in posts[:3]:
    print(post.bid, post.text[:60], post.pic_urls)

hot = client.search_posts("人工智能")
print(f"找到 {len(hot)} 条搜索结果")
```

## 图片下载示例
```python
from crawl4weibo import WeiboClient

client = WeiboClient()
post = client.get_post_by_bid("Q6FyDtbQc")

if post.pic_urls:
    results = client.download_post_images(
        post,
        download_dir="./downloads",
        subdir="featured_post",
    )
    for url, path in results.items():
        print("✅" if path else "⚠️", url, "->", path)
```
更多高级场景请参考 `examples/download_images_example.py`。

## API 能力速览
- `get_user_by_uid(uid)`：获取用户画像与计数。
- `get_user_posts(uid, page=1, expand=False)`：抓取用户首页微博，支持展开长文。
- `get_post_by_bid(bid)`：获取单条微博的完整正文与多媒体信息。
- `search_users(query, page=1, count=10)` / `search_posts(query, page=1)`：关键词搜索。
- `download_post_images(post, ...)`、`download_user_posts_images(uid, pages=2, ...)`：下载图像素材。
- 统一异常：`NetworkError`、`RateLimitError`、`UserNotFoundError` 等，便于业务兜底。

## 开发与测试
```bash
uv sync --dev                # 安装开发依赖
uv run pytest                # 运行全部测试 (内置 unit/integration/slow 标记)
uv run ruff check crawl4weibo --fix
uv run ruff format crawl4weibo
uv run python examples/simple_example.py
```
项目结构、贡献指南与更多流程请参见 `docs/DEVELOPMENT.md` 与 `AGENTS.md`。

## 许可证
MIT License
