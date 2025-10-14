#!/usr/bin/env python

"""
Crawl4Weibo 简单使用示例
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crawl4weibo import WeiboClient


def main():
    print("🚀 Crawl4Weibo 微博爬虫")
    print("=" * 30)

    client = WeiboClient()

    test_uid = "2656274875"

    try:
        print("\n📋 获取用户信息...")
        user = client.get_user_by_uid(test_uid)
        print(f"用户名: {user.screen_name}")
        print(f"粉丝数: {user.followers_count}")
        print(f"微博数: {user.posts_count}")

        print("\n📄 获取微博...")
        posts_page1 = client.get_user_posts(test_uid, page=1, expand=True)
        posts_page2 = client.get_user_posts(test_uid, page=2, expand=True)
        posts = (posts_page1 or []) + (posts_page2 or [])
        print(f"获取到 {len(posts)} 条微博")

        for i, post in enumerate(posts[:3], 1):
            print(f"  {i}. {post.text[:50]}...")
            print(f"     点赞: {post.attitudes_count} | 评论: {post.comments_count}")

        if posts:
            print("\n📋 根据ID获取单条微博...")
            first_post_bid = posts[0].bid
            print(f"获取微博ID: {first_post_bid}")
            single_post = client.get_post_by_bid(first_post_bid)
            print(f"内容: {single_post.text[:50]}...")

        print("\n🔍 搜索用户...")
        users = client.search_users("新浪")
        for user in users:
            print(f"  - {user.screen_name} (粉丝: {user.followers_count})")

        print("\n🔍 搜索微博...")
        posts = client.search_posts("人工智能", page=1)
        for post in posts:
            print(f"  - {post.text[:50]}...")

        print("\n✅ 测试完成!")

    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()
