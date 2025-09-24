#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HTML/JSON parsing utilities for crawl4weibo
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from lxml import etree

from ..exceptions.base import ParseError
from .logger import get_logger


class WeiboParser:
    """Parser for Weibo API responses and HTML content"""
    
    def __init__(self):
        self.logger = get_logger()
    
    def parse_user_info(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse user information from API response
        
        Args:
            response_data: Raw API response data
            
        Returns:
            Dict containing parsed user information
        """
        try:
            if "data" not in response_data or "userInfo" not in response_data["data"]:
                raise ParseError("Invalid user info response format")
            
            user_info = response_data["data"]["userInfo"]
            
            return {
                "id": str(user_info.get("id", "")),
                "screen_name": user_info.get("screen_name", ""),
                "gender": user_info.get("gender", ""),
                "description": user_info.get("description", ""),
                "followers_count": user_info.get("followers_count", 0),
                "following_count": user_info.get("follow_count", 0),
                "posts_count": user_info.get("statuses_count", 0),
                "verified": user_info.get("verified", False),
                "verified_reason": user_info.get("verified_reason", ""),
                "avatar_url": user_info.get("profile_image_url", ""),
                "cover_image_url": user_info.get("cover_image_phone", ""),
            }
        except Exception as e:
            self.logger.error(f"Failed to parse user info: {e}")
            raise ParseError(f"Failed to parse user info: {e}")
    
    def parse_posts(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse posts from API response
        
        Args:
            response_data: Raw API response data
            
        Returns:
            List of parsed post dictionaries
        """
        try:
            if "data" not in response_data or "cards" not in response_data["data"]:
                return []
            
            posts = []
            cards = response_data["data"]["cards"]
            
            for card in cards:
                if card.get("card_type") == 9 and "mblog" in card:
                    post_data = self._parse_single_post(card["mblog"])
                    if post_data:
                        posts.append(post_data)
                elif card.get("card_type") == 11 and "card_group" in card:
                    card_group = card.get("card_group", [])
                    for group_card in card_group:
                        if group_card.get("card_type") == 9 and "mblog" in group_card:
                            post_data = self._parse_single_post(group_card["mblog"])
                            if post_data:
                                posts.append(post_data)
            
            return posts
        except Exception as e:
            self.logger.error(f"Failed to parse posts: {e}")
            raise ParseError(f"Failed to parse posts: {e}")
    
    def _parse_single_post(self, mblog: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single post from mblog data"""
        try:
            post = {
                "id": str(mblog.get("id", "")),
                "user_id": str(mblog.get("user", {}).get("id", "")),
                "text": self._clean_text(mblog.get("text", "")),
                "created_at": self._parse_time(mblog.get("created_at", "")),
                "source": mblog.get("source", ""),
                "reposts_count": mblog.get("reposts_count", 0),
                "comments_count": mblog.get("comments_count", 0),
                "attitudes_count": mblog.get("attitudes_count", 0),
                "pic_urls": self._extract_pic_urls(mblog),
                "video_url": self._extract_video_url(mblog),
                "is_original": not mblog.get("retweeted_status"),
                "location": mblog.get("geo", {}).get("name", ""),
                "topic_ids": self._extract_topics(mblog.get("text", "")),
                "at_users": self._extract_at_users(mblog.get("text", "")),
            }
            
            if mblog.get("retweeted_status"):
                post["retweeted_status"] = self._parse_single_post(mblog["retweeted_status"])
            
            return post
        except Exception as e:
            self.logger.error(f"Failed to parse single post: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
        
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """Parse time string to datetime"""
        if not time_str:
            return None
        
        try:
            return datetime.strptime(time_str, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            try:
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                self.logger.warning(f"Failed to parse time: {time_str}")
                return None
    
    def _extract_pic_urls(self, mblog: Dict[str, Any]) -> List[str]:
        """Extract picture URLs from post"""
        pic_urls = []
        
        if "pics" in mblog:
            for pic in mblog["pics"]:
                if "large" in pic and "url" in pic["large"]:
                    pic_urls.append(pic["large"]["url"])
        
        return pic_urls
    
    def _extract_video_url(self, mblog: Dict[str, Any]) -> str:
        """Extract video URL from post"""
        if "page_info" in mblog and mblog["page_info"].get("type") == "video":
            media_info = mblog["page_info"].get("media_info", {})
            return media_info.get("stream_url", "")
        
        return ""
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topic hashtags from text"""
        if not text:
            return []
        
        topics = re.findall(r'#([^#]+)#', text)
        return [topic.strip() for topic in topics if topic.strip()]
    
    def _extract_at_users(self, text: str) -> List[str]:
        """Extract @mentioned users from text"""
        if not text:
            return []
        
        mentions = re.findall(r'@([^\s@]+)', text)
        return [mention.strip() for mention in mentions if mention.strip()]