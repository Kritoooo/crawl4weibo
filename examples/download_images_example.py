#!/usr/bin/env python

"""
图片下载功能示例 - 演示如何使用crawl4weibo下载微博图片
"""

from crawl4weibo import WeiboClient


def main():
    """演示图片下载功能"""
    
    client = WeiboClient()
    test_uid = "2656274875"
    
    print("=== 微博图片下载功能演示 ===\n")
    
    # 示例1: 下载单个帖子的图片
    print("1. 下载单个帖子的图片")
    try:
        post = client.get_post_by_bid("Q6FyDtbQc")
        if post.pic_urls:
            print(f"帖子包含 {len(post.pic_urls)} 张图片")
            download_results = client.download_post_images(
                post,
                download_dir="./example_downloads",
                subdir="single_post"
            )
            
            print("下载结果:")
            for url, path in download_results.items():
                status = "成功" if path else "失败"
                print(f"  {status}: {url}")
                if path:
                    print(f"    保存到: {path}")
        else:
            print("该帖子没有图片")
    except Exception as e:
        print(f"下载单个帖子图片失败: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 示例2: 下载用户最近帖子的图片
    print("2. 下载用户最近帖子的图片")
    try:
        posts = client.get_user_posts(test_uid, page=1)
        posts_with_images = [post for post in posts if post.pic_urls]
        
        if posts_with_images:
            print(f"找到 {len(posts_with_images)} 个包含图片的帖子")
            download_results = client.download_posts_images(
                posts_with_images[:3],  # 只下载前3个帖子的图片
                download_dir="./example_downloads",
                subdir="user_posts"
            )
            
            print("批量下载结果:")
            for post_id, post_results in download_results.items():
                print(f"  帖子 {post_id}:")
                for url, path in post_results.items():
                    status = "成功" if path else "失败"
                    print(f"    {status}: {url}")
        else:
            print("该用户最近的帖子中没有图片")
    except Exception as e:
        print(f"下载用户帖子图片失败: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 示例3: 下载用户多页帖子的图片（更全面的下载）
    print("3. 下载用户多页帖子的图片")
    try:
        download_results = client.download_user_posts_images(
            uid=test_uid,
            pages=2,  # 下载前2页的帖子
            download_dir="./example_downloads",
            expand_long_text=False
        )
        
        total_posts = len(download_results)
        total_images = sum(len(post_results) for post_results in download_results.values())
        successful_downloads = sum(
            sum(1 for path in post_results.values() if path is not None)
            for post_results in download_results.values()
        )
        
        print(f"下载统计:")
        print(f"  处理帖子数: {total_posts}")
        print(f"  总图片数: {total_images}")
        print(f"  成功下载: {successful_downloads}")
        print(f"  成功率: {(successful_downloads/total_images*100):.1f}%" if total_images > 0 else "无图片")
        
    except Exception as e:
        print(f"批量下载用户图片失败: {e}")
    
    print("\n=== 演示完成 ===")
    print("下载的图片保存在 ./example_downloads/ 目录中")


if __name__ == "__main__":
    main()