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
test_uid = "2656274875"

# 获取用户信息
user = client.get_user_by_uid(test_uid)
print(f"用户名: {user.screen_name}")
print(f"粉丝数: {user.followers_count}")
print(f"微博数: {user.posts_count}")

# 获取微博
posts_page1 = client.get_user_posts(test_uid, page=1)
posts_page2 = client.get_user_posts(test_uid, page=2)
posts = (posts_page1 or []) + (posts_page2 or [])
print(f"获取到 {len(posts)} 条微博")
for i, post in enumerate(posts[:3], 1):
    print(f"  {i}. {post.text[:50]}...")
    print(f"     点赞: {post.attitudes_count} | 评论: {post.comments_count}")

# 根据微博ID获取单条微博
post = client.get_post_by_bid("Q6FyDtbQc")
print(f"微博内容: {post.text[:50]}")
# print(f"发布时间: {post.created_at}")
# print(f"图片数量: {len(post.pic_urls)}")

# 搜索用户
users = client.search_users("新浪")
for user in users:
    print(f"  - {user.screen_name} (粉丝: {user.followers_count})")
        
# 搜索微博
posts = client.search_posts("人工智能", page=1)
for post in posts:
    print(f"  - {post.text[:50]}...")
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
- `get_post_by_bid(bid)` - 根据微博ID获取单条微博
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
