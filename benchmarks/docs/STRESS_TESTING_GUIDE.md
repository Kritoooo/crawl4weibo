# crawl4weibo 压力测试指南

本指南介绍如何对 crawl4weibo 进行**真实场景**的压力测试和性能评估。

## 核心思想

本测试工具模拟真实的爬虫工作流程：

```
1. 搜索话题/关键词 → 2. 提取博文 BID → 3. 爬取详细内容 → 4. 统计吞吐量
```

**主要性能指标：每秒爬取的博文数量 (posts/second)**

## 目录

- [快速开始](#快速开始)
- [测试模式](#测试模式)
- [使用方法](#使用方法)
- [性能指标说明](#性能指标说明)
- [实战示例](#实战示例)
- [结果分析](#结果分析)

## 快速开始

### 方法 1: 命令行交互式测试（推荐）

```bash
cd benchmarks
python test_performance.py
```

按提示输入：
- Cookies（可选）
- 代理 API URL（可选）
- 搜索关键词（如："Python"）
- 测试类型（1-4）

### 方法 2: 使用 pytest

```bash
# 运行所有性能测试
pytest benchmarks/test_performance.py -v -m integration

# 运行特定测试
pytest benchmarks/test_performance.py::test_sequential_topic_crawl -v
pytest benchmarks/test_performance.py::test_concurrent_topic_crawl -v
pytest benchmarks/test_performance.py::test_timed_crawl -v
pytest benchmarks/test_performance.py::test_proxy_comparison -v
```

### 方法 3: 编程方式

```python
from benchmarks.test_performance import TopicCrawler

# 初始化爬虫
crawler = TopicCrawler(
    cookies="your_cookies_here",
    proxy_api_url="http://proxy-api.com/get"
)

# 运行顺序测试
metrics = crawler.crawl_topic_sequential(
    query="Python编程",
    search_pages=2,
    max_posts=20
)

# 打印结果
metrics.print_summary()

# 查看关键指标
print(f"吞吐量: {metrics.posts_per_second:.3f} posts/s")
print(f"成功率: {metrics.overall_success_rate:.2f}%")
```

## 测试模式

### 1. 顺序爬取 (Sequential Crawl)

单线程顺序爬取，用于测试基础性能。

```python
metrics = crawler.crawl_topic_sequential(
    query="人工智能",      # 搜索关键词
    search_pages=2,       # 搜索2页
    max_posts=20          # 最多爬取20条博文
)
```

**工作流程：**
1. 搜索第1页 → 提取 BIDs → 搜索第2页 → 提取 BIDs
2. 逐个爬取每条博文的详细内容

**适用场景：**
- 了解单客户端的基准性能
- 调试和问题排查
- 验证功能正确性

### 2. 并发爬取 (Concurrent Crawl)

多线程并发爬取详情，提升吞吐量。

```python
metrics = crawler.crawl_topic_concurrent(
    query="Python",
    search_pages=3,
    max_posts=50,
    num_workers=10        # 10个工作线程并发爬取
)
```

**工作流程：**
1. 顺序搜索，收集所有 BIDs
2. 使用线程池并发爬取详情

**适用场景：**
- 测试最大吞吐量
- 评估并发性能
- 模拟多用户场景

### 3. 定时爬取 (Timed Crawl)

在固定时间内持续爬取，测试稳定性。

```python
metrics = crawler.crawl_topic_timed(
    query="科技",
    duration_seconds=60,  # 持续60秒
    num_workers=5,        # 5个并发工作线程
    search_pages=5        # 预先搜索5页建立BID池
)
```

**工作流程：**
1. 预先搜索多页，建立 BID 池
2. 在指定时间内循环爬取 BID 池中的博文
3. 实时显示爬取速率

**适用场景：**
- 测试持续运行的稳定性
- 评估长时间的平均吞吐量
- 发现内存泄漏等问题

### 4. 代理对比 (Proxy Comparison)

对比使用代理和不使用代理的性能差异。

```python
results = crawler.compare_proxy_performance(
    query="微博",
    search_pages=1,
    max_posts=10
)

# 结果包含两个指标对象
# results['no_proxy']    - 无代理
# results['with_proxy']  - 使用代理
```

**适用场景：**
- 评估代理对性能的影响
- 选择最优代理服务商
- 成本收益分析

## 性能指标说明

### 主要指标

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| **Posts Crawled/Second** | **每秒爬取博文数**（核心指标） | 爬取成功的博文数 / 总耗时 |
| Total Posts Crawled | 成功爬取的博文总数 | - |
| Total Time | 总耗时（秒） | - |

### 搜索阶段指标

| 指标 | 说明 |
|------|------|
| Search Requests | 搜索请求次数 |
| Search Success Rate | 搜索成功率 (%) |
| Posts Found (BIDs) | 找到的博文 BID 总数 |
| Avg Search Time | 平均搜索响应时间 (秒) |

### 详情爬取阶段指标

| 指标 | 说明 |
|------|------|
| Detail Requests | 详情请求次数 |
| Detail Success Rate | 详情爬取成功率 (%) |
| Avg Detail Time | 平均详情爬取时间 (秒) |
| P50/P95/P99 | 响应时间百分位数 |

### 示例输出

```
================================================================================
                        Crawling Performance Test
================================================================================

🎯 PRIMARY METRIC
Posts Crawled/Second:     0.156 posts/s
Total Posts Crawled:      18
Total Time:               115.23s

📊 SEARCH PHASE
Search Requests:          2
  Successful:             2
  Failed:                 0
  Success Rate:           100.00%
Posts Found (BIDs):       20
Avg Search Time:          3.45s
Total Search Time:        6.90s

📝 DETAIL CRAWLING PHASE
Detail Requests:          20
  Successful:             18
  Failed:                 2
  Success Rate:           90.00%
Avg Detail Time:          5.42s
Total Detail Time:        108.33s

📈 OVERALL STATISTICS
Total Requests:           22
Overall Success Rate:     90.91%
Unique Posts Crawled:     18
Failed Posts:             2

⏱️  DETAIL RESPONSE TIME PERCENTILES
  Min:                    2.34s
  P50 (Median):           5.12s
  P95:                    9.87s
  P99:                    11.23s
  Max:                    11.45s

❌ ERROR SUMMARY
  ParseError: 1
  NetworkError: 1
================================================================================
```

## 实战示例

### 场景 1: 评估基础爬取能力

测试爬取"Python编程"话题的博文，了解基准性能。

```python
from benchmarks.test_performance import TopicCrawler

crawler = TopicCrawler(cookies="your_cookies")

# 顺序爬取
metrics = crawler.crawl_topic_sequential(
    query="Python编程",
    search_pages=2,      # 搜索2页
    max_posts=20         # 最多20条
)

metrics.print_summary()

# 预期结果：
# - 吞吐量约 0.15-0.25 posts/s（考虑内置延迟）
# - 成功率 > 90%
# - 平均详情时间 3-6秒
```

### 场景 2: 测试并发性能提升

对比不同并发数的吞吐量提升。

```python
query = "人工智能"
search_pages = 3
max_posts = 50

# 单线程
metrics_1 = crawler.crawl_topic_sequential(query, search_pages, max_posts)

# 5线程并发
metrics_5 = crawler.crawl_topic_concurrent(query, search_pages, max_posts, num_workers=5)

# 10线程并发
metrics_10 = crawler.crawl_topic_concurrent(query, search_pages, max_posts, num_workers=10)

# 对比结果
print(f"\n并发性能对比:")
print(f"单线程:   {metrics_1.posts_per_second:.3f} posts/s")
print(f"5并发:    {metrics_5.posts_per_second:.3f} posts/s (提升 {metrics_5.posts_per_second/metrics_1.posts_per_second:.1f}x)")
print(f"10并发:   {metrics_10.posts_per_second:.3f} posts/s (提升 {metrics_10.posts_per_second/metrics_1.posts_per_second:.1f}x)")
```

### 场景 3: 持续压力测试

运行5分钟的持续爬取，测试稳定性。

```python
# 5分钟持续压力测试
metrics = crawler.crawl_topic_timed(
    query="科技新闻",
    duration_seconds=300,    # 5分钟
    num_workers=5,
    search_pages=10          # 预先搜索10页建立大的BID池
)

metrics.print_summary("5分钟持续压力测试")

# 关注指标：
# - 吞吐量是否稳定
# - 成功率是否下降
# - 是否有内存泄漏
# - 错误率是否上升
```

### 场景 4: 代理池性能评估

评估代理对性能的影响。

```python
# 对比不同代理配置
proxy_services = [
    ("http://proxy1.com/api/get", "服务商A"),
    ("http://proxy2.com/api/get", "服务商B"),
]

for proxy_url, name in proxy_services:
    crawler = TopicCrawler(cookies="your_cookies", proxy_api_url=proxy_url)

    results = crawler.compare_proxy_performance(
        query="Python",
        search_pages=2,
        max_posts=20
    )

    print(f"\n{name} 性能:")
    print(f"  无代理: {results['no_proxy'].posts_per_second:.3f} posts/s, "
          f"{results['no_proxy'].overall_success_rate:.2f}% 成功率")
    print(f"  有代理: {results['with_proxy'].posts_per_second:.3f} posts/s, "
          f"{results['with_proxy'].overall_success_rate:.2f}% 成功率")
```

### 场景 5: 寻找最优并发数

找出性能最佳的并发线程数。

```python
query = "微博热搜"
search_pages = 5
max_posts = 100

results = {}
worker_counts = [1, 3, 5, 10, 15, 20]

for workers in worker_counts:
    print(f"\n测试 {workers} 个工作线程...")
    metrics = crawler.crawl_topic_concurrent(
        query=query,
        search_pages=search_pages,
        max_posts=max_posts,
        num_workers=workers
    )
    results[workers] = metrics

# 找出最优配置
best_workers = max(results.items(), key=lambda x: x[1].posts_per_second)
print(f"\n最优配置: {best_workers[0]} 个工作线程")
print(f"吞吐量: {best_workers[1].posts_per_second:.3f} posts/s")
print(f"成功率: {best_workers[1].overall_success_rate:.2f}%")

# 绘制性能曲线
print(f"\n{'Workers':<10} {'Posts/s':<15} {'Success Rate':<15}")
print("-" * 40)
for workers, metrics in sorted(results.items()):
    print(f"{workers:<10} {metrics.posts_per_second:<15.3f} {metrics.overall_success_rate:<15.2f}%")
```

## 结果分析

### 健康指标 ✅

- **吞吐量**:
  - 单线程 > 0.15 posts/s
  - 5并发 > 0.5 posts/s
  - 10并发 > 0.8 posts/s

- **成功率**:
  - 搜索成功率 > 95%
  - 详情成功率 > 90%
  - 总体成功率 > 90%

- **响应时间**:
  - P95 < 10秒
  - P99 < 15秒

### 警告指标 ⚠️

- 成功率 80-90%
- 吞吐量下降 > 30%
- P95 响应时间 10-20秒
- 偶发 ParseError 或 NetworkError

### 问题指标 ❌

- **成功率 < 80%** → 可能触发反爬虫，需要降低频率或更换代理
- **吞吐量 < 0.1 posts/s** → 网络或代理问题
- **大量 432 错误** → 触发微博反爬虫，需立即停止
- **P95 > 20秒** → 代理质量差或网络问题

### 性能优化建议

#### 提升吞吐量
1. **增加并发数**：测试找出最优并发数（通常 5-10 个线程）
2. **使用高质量代理**：选择响应快、成功率高的代理
3. **预先搜索更多页**：在定时测试中建立大的 BID 池

#### 提高成功率
1. **降低请求频率**：减少并发数
2. **使用代理池**：轮换 IP 避免封禁
3. **添加重试逻辑**：对失败的请求重试

#### 降低响应时间
1. **选择地理位置近的代理**
2. **过滤慢速代理**：监控代理响应时间
3. **优化网络配置**：使用更快的网络

## 最佳实践

### 1. 测试前准备

- ✅ 确保 cookies 有效且未过期
- ✅ 网络连接稳定
- ✅ 准备真实存在的搜索关键词
- ✅ 了解目标 API 的速率限制

### 2. 测试策略

**渐进式测试**：
```
Step 1: 顺序测试 (10条) → 验证功能
Step 2: 顺序测试 (50条) → 测试基准性能
Step 3: 并发测试 (50条, 5并发) → 测试并发性能
Step 4: 定时测试 (60秒) → 测试稳定性
Step 5: 并发测试 (100条, 最优并发数) → 测试极限性能
```

### 3. 安全建议

⚠️ **避免过度请求**
- 不要使用超过 20 个并发线程
- 长时间测试建议间隔休息
- 监控错误率，及时停止

⚠️ **保护账号安全**
- 使用测试账号，不用主账号
- 不要在公共环境暴露 cookies
- 定期更换 cookies

⚠️ **遵守规则**
- 尊重 robots.txt
- 不对服务器造成过大压力
- 遵守网站服务条款

### 4. 结果记录

建议记录每次测试的关键信息：

```python
# 测试记录模板
test_record = {
    "date": "2025-01-15",
    "query": "Python编程",
    "mode": "concurrent",
    "workers": 5,
    "max_posts": 50,
    "proxy": "proxy-service-A",
    "results": {
        "posts_per_second": 0.625,
        "success_rate": 92.5,
        "avg_detail_time": 4.8,
        "total_time": 80.0
    },
    "notes": "使用新代理服务商，性能提升明显"
}
```

## 常见问题

### Q1: 为什么吞吐量很低？

**可能原因：**
- 内置延迟（1-3秒）限制了速度
- 网络延迟高
- 代理速度慢
- 并发数不足

**解决方案：**
- 增加并发数（推荐 5-10）
- 使用更快的代理
- 检查网络状况

### Q2: 为什么成功率下降？

**可能原因：**
- 触发反爬虫机制
- 代理被封禁
- Cookies 过期
- 请求频率过高

**解决方案：**
- 降低并发数和请求频率
- 更换代理或代理服务商
- 更新 cookies
- 添加更长的延迟

### Q3: 如何选择合适的并发数？

**建议：**
- 从小到大逐步测试：1 → 3 → 5 → 10 → 15
- 观察吞吐量和成功率的变化
- 选择吞吐量最高且成功率 > 90% 的配置
- 通常 5-10 个并发是最优的

### Q4: 定时测试为什么要预先搜索？

**原因：**
- 搜索操作相对耗时（每页 3-5 秒）
- 预先搜索可以建立 BID 池
- 测试阶段专注于详情爬取性能
- 避免重复搜索相同内容

### Q5: 如何解读响应时间百分位数？

**含义：**
- P50（中位数）：50% 的请求在此时间内完成
- P95：95% 的请求在此时间内完成
- P99：99% 的请求在此时间内完成

**建议：**
- 关注 P95 和 P99，它们反映极端情况
- P95 > 10秒 需要优化
- P99 > 20秒 说明有严重问题

## 进阶功能

### 自定义测试

你可以根据需要修改测试脚本：

```python
# 修改 benchmarks/test_performance.py

class TopicCrawler:
    # 添加自定义测试方法
    def crawl_topic_custom(self, query, custom_param):
        # 你的自定义逻辑
        pass
```

### 集成到 CI/CD

```yaml
# .github/workflows/performance-test.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * 0'  # 每周日凌晨2点运行

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Run performance tests
        run: |
          pytest benchmarks/test_performance.py::test_timed_crawl -v
        env:
          WEIBO_COOKIES: ${{ secrets.WEIBO_COOKIES }}
```

### 结果可视化

```python
import matplotlib.pyplot as plt

# 收集多次测试数据
worker_counts = [1, 3, 5, 10, 15, 20]
throughputs = []

for workers in worker_counts:
    metrics = crawler.crawl_topic_concurrent(
        query="Python", search_pages=3, max_posts=50, num_workers=workers
    )
    throughputs.append(metrics.posts_per_second)

# 绘图
plt.plot(worker_counts, throughputs, marker='o')
plt.xlabel('Number of Workers')
plt.ylabel('Posts per Second')
plt.title('Throughput vs Concurrency')
plt.grid(True)
plt.savefig('performance_curve.png')
```

## 相关资源

- [项目主 README](../README.md)
- [架构分析文档](ARCHITECTURE_ANALYSIS.md)
- [API 快速参考](QUICK_REFERENCE.md)

## 反馈

如有问题或建议，欢迎提交 Issue 或 Pull Request！
