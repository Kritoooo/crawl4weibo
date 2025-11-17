#!/usr/bin/env python

"""
Image Download Example - Demonstrates how to use crawl4weibo to download Weibo images
"""

from crawl4weibo import WeiboClient


def main():
    """Demonstrates image download functionality"""

    client = WeiboClient()
    test_uid = "2656274875"

    print("=== Weibo Image Download Functionality Demo ===\n")

    # Example 1: Download images from a single post
    print("1. Download images from a single post")
    try:
        post = client.get_post_by_bid("Q6FyDtbQc")
        if post.pic_urls:
            print(f"Post contains {len(post.pic_urls)} images")
            download_results = client.download_post_images(
                post,
                download_dir="./example_downloads",
                subdir="single_post"
            )

            print("Download results:")
            for url, path in download_results.items():
                status = "Success" if path else "Failed"
                print(f"  {status}: {url}")
                if path:
                    print(f"    Saved to: {path}")
        else:
            print("This post has no images")
    except Exception as e:
        print(f"Failed to download single post images: {e}")
    
    print("\n" + "="*50 + "\n")

    # Example 2: Download images from user's recent posts
    print("2. Download images from user's recent posts")
    try:
        posts = client.get_user_posts(test_uid, page=1)
        posts_with_images = [post for post in posts if post.pic_urls]

        if posts_with_images:
            print(f"Found {len(posts_with_images)} posts with images")
            download_results = client.download_posts_images(
                posts_with_images[:3],  # Download images from first 3 posts only
                download_dir="./example_downloads",
                subdir="user_posts"
            )

            print("Batch download results:")
            for post_id, post_results in download_results.items():
                print(f"  Post {post_id}:")
                for url, path in post_results.items():
                    status = "Success" if path else "Failed"
                    print(f"    {status}: {url}")
        else:
            print("No images found in user's recent posts")
    except Exception as e:
        print(f"Failed to download user post images: {e}")
    
    print("\n" + "="*50 + "\n")

    # Example 3: Download images from multiple pages of user posts (comprehensive download)
    print("3. Download images from multiple pages of user posts")
    try:
        download_results = client.download_user_posts_images(
            uid=test_uid,
            pages=2,  # Download from first 2 pages of posts
            download_dir="./example_downloads",
            expand_long_text=False
        )

        total_posts = len(download_results)
        total_images = sum(len(post_results) for post_results in download_results.values())
        successful_downloads = sum(
            sum(1 for path in post_results.values() if path is not None)
            for post_results in download_results.values()
        )

        print("Download statistics:")
        print(f"  Posts processed: {total_posts}")
        print(f"  Total images: {total_images}")
        print(f"  Successfully downloaded: {successful_downloads}")
        print(f"  Success rate: {(successful_downloads/total_images*100):.1f}%" if total_images > 0 else "No images")

    except Exception as e:
        print(f"Failed to batch download user images: {e}")

    print("\n=== Demo completed ===")
    print("Downloaded images are saved in the ./example_downloads/ directory")


if __name__ == "__main__":
    main()