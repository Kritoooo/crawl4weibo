# Crawl4Weibo

一个开箱即用的微博爬虫Python库，基于实际测试成功的方案，无需Cookie即可使用。

## 特性

- 🚀 **开箱即用**: 无需Cookie，一行代码初始化
- 🛡️ **防反爬**: 自动处理432错误和请求限制  
- 📱 **真实模拟**: 使用真实手机浏览器UA
- 🔄 **智能重试**: 自动重试机制
- 📊 **结构化数据**: 清晰的数据模型

## 安装

```bash
pip install crawl4weibo
```

## 快速开始

```python
from crawl4weibo import WeiboClient

# 初始化（无需Cookie）
client = WeiboClient()

# 获取用户信息
user = client.get_user_by_uid("1195230310")
print(f"用户: {user.screen_name}")
print(f"粉丝: {user.followers_count:,}")

# 获取微博
posts = client.get_user_posts("1195230310")
for post in posts:
    print(f"微博: {post.text[:50]}...")
    print(f"点赞: {post.attitudes_count}")

# 搜索用户
users = client.search_users("技术博主")
for user in users:
    print(f"用户: {user.screen_name}")

# 搜索微博  
posts = client.search_posts("人工智能")
for post in posts:
    print(f"内容: {post.text[:50]}...")
```

## API参考

### WeiboClient

#### 初始化
```python
WeiboClient(cookies=None, log_level="INFO", log_file=None)
```

#### 主要方法

- `get_user_by_uid(uid)` - 获取用户信息
- `get_user_posts(uid, page=1)` - 获取用户微博
- `search_users(query, page=1, count=10)` - 搜索用户
- `search_posts(query, page=1)` - 搜索微博

## 运行示例

```bash
python examples/simple_example.py
```

## 技术实现

基于你提供的成功代码实现：

```python
# 核心技术栈
- Android Chrome UA模拟
- 移动端API接口
- 自动session管理  
- 432错误智能重试
- 随机请求间隔
```

## 许可证

MIT License