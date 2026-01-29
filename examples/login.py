from crawl4weibo import WeiboClient

client = WeiboClient(
    login_cookies=True,
    browser_headless=False,
    login_timeout=180,
)