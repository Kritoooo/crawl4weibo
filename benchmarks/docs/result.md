# one-time proxy mode vs long time mode

Version: Commit d7a188e, Concurrent crawl (multi-threaded)
```
================================================================================
                             Concurrent Crawl Test                              
================================================================================

🎯 PRIMARY METRIC
Posts Crawled/Second:     0.849 posts/s
Total Posts Crawled:      194
Actual Elapsed Time:      228.60s
Concurrency Speedup:      3.75x

📊 SEARCH PHASE
Search Requests:          20
  Successful:             20
  Failed:                 0
  Success Rate:           100.00%
Posts Found (BIDs):       194
Avg Search Time:          6.70s
Sum of Search Times:      133.99s (all requests added)

📝 DETAIL CRAWLING PHASE
Detail Requests:          194
  Successful:             194
  Failed:                 0
  Success Rate:           100.00%
Avg Detail Time:          4.42s
Sum of Detail Times:      858.27s (all requests added)

📈 OVERALL STATISTICS
Total Requests:           214
Overall Success Rate:     100.00%
Unique Posts Crawled:     182
Failed Posts:             0

⏱️  DETAIL RESPONSE TIME PERCENTILES
  Min:                    2.47s
  P50 (Median):           4.05s
  P95:                    8.47s
  P99:                    12.24s
  Max:                    14.89s
================================================================================
```
```
================================================================================
                             Concurrent Crawl Test                              
================================================================================

🎯 PRIMARY METRIC
Posts Crawled/Second:     1.219 posts/s
Total Posts Crawled:      194
Actual Elapsed Time:      159.13s
Concurrency Speedup:      3.29x

📊 SEARCH PHASE
Search Requests:          20
  Successful:             20
  Failed:                 0
  Success Rate:           100.00%
Posts Found (BIDs):       194
Avg Search Time:          4.52s
Sum of Search Times:      90.32s (all requests added)

📝 DETAIL CRAWLING PHASE
Detail Requests:          194
  Successful:             194
  Failed:                 0
  Success Rate:           100.00%
Avg Detail Time:          2.70s
Sum of Detail Times:      522.84s (all requests added)

📈 OVERALL STATISTICS
Total Requests:           214
Overall Success Rate:     100.00%
Unique Posts Crawled:     184
Failed Posts:             0

⏱️  DETAIL RESPONSE TIME PERCENTILES
  Min:                    0.58s
  P50 (Median):           1.64s
  P95:                    6.90s
  P99:                    16.58s
  Max:                    16.61s
================================================================================
```



