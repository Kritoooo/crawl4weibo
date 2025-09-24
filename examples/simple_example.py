#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Crawl4Weibo 简单使用示例
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawl4weibo import WeiboClient


def main():
    """基本使用示例"""
    
    print("🚀 Crawl4Weibo 微博爬虫")
    print("=" * 30)
    
    # 初始化客户端（无需Cookie）
    client = WeiboClient()
    
    # 测试用户
    test_uid = "1195230310"  # 微博官方
    
    try:
        # 获取用户信息
        print(f"\n📋 获取用户信息...")
        user = client.get_user_by_uid(test_uid)
        print(f"用户名: {user.screen_name}")
        print(f"粉丝数: {user.followers_count}")
        print(f"微博数: {user.posts_count}")
        
        # 获取微博
        print(f"\n📄 获取微博...")
        posts = client.get_user_posts(test_uid, page=1)
        print(f"获取到 {len(posts)} 条微博")
        
        for i, post in enumerate(posts[:3], 1):
            print(f"  {i}. {post.text[:50]}...")
            print(f"     点赞: {post.attitudes_count} | 评论: {post.comments_count}")
        
        # 搜索用户
        print(f"\n🔍 搜索用户...")
        users = client.search_users("新浪")
        for user in users:
            print(f"  - {user.screen_name} (粉丝: {user.followers_count})")
                
        # 搜索微博
        print(f"\n🔍 搜索微博...")
        posts = client.search_posts("人工智能", page=1)
        for post in posts:
            print(f"  - {post.text[:50]}...")

        print("\n✅ 测试完成!")

    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()