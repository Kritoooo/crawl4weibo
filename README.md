# Crawl4Weibo

Crawl4Weibo 是一个开箱即用的微博爬虫 Python 库，模拟移动端请求、处理常见反爬策略，并返回结构化数据模型，适合数据采集、分析与监控场景。

## ✨ 特性
- 无需 Cookie 即可运行，自动初始化 session 和移动端 UA。
- 内置 432 防护处理与指数退避重试，减少请求失败。
- 支持动态和静态IP代理池统一管理，可配置过期时间，支持轮询和自动清理。
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

## 代理池配置示例
```python
from crawl4weibo import WeiboClient

# 方式1: 使用动态代理API（自动获取并加入池中，池未满时自动拉取）
client = WeiboClient(
    proxy_api_url="http://api.proxy.com/get?format=json",
    dynamic_proxy_ttl=300,      # 动态代理过期时间（秒），默认300
    proxy_pool_size=10,         # IP池容量，默认10
    proxy_fetch_strategy="random"  # 获取策略：random(随机) 或 round_robin(轮询)
)

# 方式2: 手动添加静态代理到IP池
client = WeiboClient()
client.add_proxy("http://1.2.3.4:8080", ttl=600)  # 指定过期时间
client.add_proxy("http://5.6.7.8:8080")  # 永不过期（ttl=None）

# 方式3: 混合使用动态和静态代理
client = WeiboClient(
    proxy_api_url="http://api.proxy.com/get",
    proxy_pool_size=20,  # 设置更大的池容量
)
client.add_proxy("http://1.2.3.4:8080", ttl=None)  # 添加永久静态代理

# IP池管理
print(f"当前可用代理数: {client.get_proxy_pool_size()}")
client.clear_proxy_pool()  # 清空IP池

# 自定义解析器：适配不同代理服务商
def my_parser(data):
    return f"http://{data['result']['ip']}:{data['result']['port']}"

client = WeiboClient(
    proxy_api_url="http://custom-api.com/proxy",
    proxy_api_parser=my_parser
)

# 灵活控制：单次请求可选择不使用代理
user = client.get_user_by_uid("2656274875", use_proxy=False)
posts = client.get_user_posts("2656274875", page=1)  # 使用代理
```

**代理池工作机制：**
- IP池未满时，自动从动态API获取新代理并加入池中
- IP池已满时，直接从池中按策略（随机/轮询）选择代理
- 过期代理会自动清理，释放容量供新代理使用

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
