# 性能测试改进说明

## 🔧 已修复的问题

### 1. ✅ Client 复用优化

**问题：** 之前每次爬取一个博文都会创建一个新的 WeiboClient 实例，导致：
- 频繁创建/销毁连接，浪费资源
- 代理池无法有效复用
- 性能下降

**解决方案：** 现在每个 worker 线程维护一个 client 实例，在整个生命周期内复用：

```python
def worker_task(worker_id: int):
    """每个 worker 维护一个 client"""
    worker_client = self._create_client()  # 只创建一次

    while not bid_queue.empty():
        bid = bid_queue.get_nowait()
        # 复用同一个 client
        self._crawl_post_detail(worker_client, bid, metrics)
```

**改进效果：**
- 减少连接开销
- 提升并发性能
- 代理池更有效

### 2. ✅ 详细错误信息

**问题：** 之前只显示错误类型，无法看到具体错误原因，难以调试。

**解决方案：** 新增 `ErrorDetail` 类，记录完整错误信息：

```python
@dataclass
class ErrorDetail:
    """错误详情记录"""
    bid: str = ""              # 失败的博文 BID
    error_type: str = ""       # 错误类型
    error_message: str = ""    # 完整错误消息
    timestamp: float = 0.0     # 错误时间戳
```

**新的错误显示：**

```
❌ ERROR SUMMARY

  ParseError: 5 occurrences
    Example 1: BID: Nzw8xB3k2
              Message: Post data not found in response
    Example 2: BID: Nzw7yA2j1
              Message: Invalid JSON response from server
    Example 3: BID: Nzw6pC1h9
              Message: Missing required field 'created_at'
    ... and 2 more

  NetworkError: 3 occurrences
    Example 1: BID: Nzw5mD0g8
              Message: Connection timeout after 5 seconds
    ... and 2 more

  💡 Tip: Call metrics.export_error_log('filename.txt') to export full error details
```

### 3. ✅ 错误日志导出

新增 `export_error_log()` 方法，可以导出完整的错误日志到文件：

```python
# 运行测试
metrics = crawler.crawl_topic_concurrent(
    query="Python",
    search_pages=2,
    max_posts=50,
    num_workers=5
)

# 查看摘要
metrics.print_summary()

# 如果有错误，导出详细日志
if metrics.detail_failed > 0:
    metrics.export_error_log("debug_errors.txt")
```

**导出的日志格式：**

```
================================================================================
CRAWL4WEIBO PERFORMANCE TEST ERROR LOG
================================================================================

DETAIL CRAWLING ERRORS:
--------------------------------------------------------------------------------

Error #1:
  BID: Nzw8xB3k2
  Type: ParseError
  Time: 1737500000.123
  Message: Failed to parse post data: Missing required field 'text'

Error #2:
  BID: Nzw7yA2j1
  Type: NetworkError
  Time: 1737500005.456
  Message: HTTPError: 432 Client Error: Too Many Requests

...

================================================================================
Total Errors: 15
================================================================================
```

## 📊 改进后的使用示例

### 基础使用（自动显示错误摘要）

```python
from tests.test_performance import TopicCrawler

crawler = TopicCrawler(cookies="your_cookies")

metrics = crawler.crawl_topic_concurrent(
    query="Python编程",
    search_pages=3,
    max_posts=50,
    num_workers=5
)

# 打印结果（会自动显示错误摘要）
metrics.print_summary()
```

### 调试失败问题

```python
# 运行测试
metrics = crawler.crawl_topic_sequential(
    query="人工智能",
    search_pages=2,
    max_posts=20
)

# 查看结果
metrics.print_summary()

# 检查成功率
if metrics.detail_success_rate < 80:
    print(f"\n⚠️  成功率过低！正在导出错误日志...")
    metrics.export_error_log("low_success_rate_errors.txt")

    # 分析错误类型
    error_types = {}
    for err in metrics.detail_errors:
        error_types[err.error_type] = error_types.get(err.error_type, 0) + 1

    print(f"\n错误类型分布：")
    for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type}: {count}")

    # 给出建议
    if error_types.get('NetworkError', 0) > 5:
        print("\n💡 建议：NetworkError 较多，可能是网络或代理问题")
    if error_types.get('ParseError', 0) > 5:
        print("\n💡 建议：ParseError 较多，可能是 API 返回格式变化")
```

### 对比不同配置的错误率

```python
# 测试不同并发数的错误率
configs = [
    {"workers": 1, "name": "单线程"},
    {"workers": 5, "name": "5并发"},
    {"workers": 10, "name": "10并发"},
    {"workers": 20, "name": "20并发"},
]

results = []
for config in configs:
    print(f"\n测试 {config['name']}...")

    metrics = crawler.crawl_topic_concurrent(
        query="科技",
        search_pages=2,
        max_posts=30,
        num_workers=config['workers']
    )

    results.append({
        "name": config['name'],
        "success_rate": metrics.detail_success_rate,
        "error_count": metrics.detail_failed,
        "throughput": metrics.posts_per_second
    })

    # 如果错误多，导出日志
    if metrics.detail_failed > 5:
        metrics.export_error_log(f"errors_{config['workers']}_workers.txt")

# 对比结果
print(f"\n{'配置':<10} {'成功率':<10} {'错误数':<10} {'吞吐量':<15}")
print("-" * 50)
for r in results:
    print(f"{r['name']:<10} {r['success_rate']:<10.2f}% {r['error_count']:<10} {r['throughput']:<15.3f} posts/s")
```

## 🎯 调试技巧

### 1. 快速定位问题

当测试失败率高时，查看错误摘要的前几个例子：

```
❌ ERROR SUMMARY

  ParseError: 15 occurrences
    Example 1: BID: Nzw8xB3k2
              Message: Post Nzw8xB3k2 not found
```

如果所有错误都是 "Post not found"，说明搜索返回的 BID 是无效的。

### 2. 时间序列分析

导出错误日志后，可以分析错误发生的时间模式：

```python
import time

# 分析错误时间分布
if metrics.detail_errors:
    error_times = [err.timestamp for err in metrics.detail_errors]
    start_time = metrics.start_time

    print("\n错误时间分布：")
    for i, err in enumerate(metrics.detail_errors[:10], 1):
        elapsed = err.timestamp - start_time
        print(f"  错误 {i}: 第 {elapsed:.1f} 秒, BID: {err.bid}, 类型: {err.error_type}")
```

如果错误集中在测试开始或结束，可能是特定时间段的问题。

### 3. 按错误类型过滤

```python
# 只查看特定类型的错误
parse_errors = [err for err in metrics.detail_errors if err.error_type == "ParseError"]
network_errors = [err for err in metrics.detail_errors if err.error_type == "NetworkError"]

print(f"ParseError 数量: {len(parse_errors)}")
print(f"NetworkError 数量: {len(network_errors)}")

# 查看 ParseError 的具体消息
if parse_errors:
    print("\nParseError 示例：")
    for err in parse_errors[:5]:
        print(f"  BID: {err.bid}")
        print(f"  消息: {err.error_message}")
```

## 🚀 性能优化建议

### 基于错误分析优化

1. **如果 NetworkError 很多：**
   - 降低并发数
   - 更换代理服务商
   - 增加请求超时时间

2. **如果 ParseError 很多：**
   - 检查 API 是否变化
   - 验证搜索结果的 BID 是否有效
   - 检查 cookies 是否过期

3. **如果特定 BID 重复失败：**
   - 可能是该博文已被删除
   - 可能是权限问题（私密博文）
   - 过滤掉这些 BID

### Worker 数量优化

现在 client 复用后，可以更安全地增加并发数：

```python
# 测试最优 worker 数量
for workers in [1, 3, 5, 10, 15, 20, 30]:
    metrics = crawler.crawl_topic_concurrent(
        query="测试",
        search_pages=2,
        max_posts=50,
        num_workers=workers
    )

    print(f"{workers} workers: {metrics.posts_per_second:.3f} posts/s, "
          f"{metrics.detail_success_rate:.1f}% 成功率")

    # 如果成功率开始下降，说明达到瓶颈
    if metrics.detail_success_rate < 85:
        print(f"⚠️  {workers} 个 workers 时成功率下降到 {metrics.detail_success_rate:.1f}%")
        break
```

## 📝 最佳实践

1. **始终检查错误摘要**：每次测试后查看错误类型和数量
2. **成功率 < 90% 时导出日志**：详细分析问题原因
3. **记录测试配置和结果**：便于对比和优化
4. **渐进式增加压力**：从小并发开始，观察错误率变化
5. **使用不同关键词测试**：避免单一测试场景的偏差

## 📌 注意事项

- 错误日志可能包含敏感信息（如 BID），分享前请检查
- 大量错误时日志文件可能很大，注意磁盘空间
- 错误时间戳使用 Unix timestamp，可用 `datetime.fromtimestamp()` 转换
