#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Post model for crawl4weibo
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Post:
    """Weibo post model"""
    
    id: str
    user_id: str
    text: str = ""
    created_at: Optional[datetime] = None
    source: str = ""
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0
    pic_urls: List[str] = field(default_factory=list)
    video_url: str = ""
    is_original: bool = True
    retweeted_status: Optional["Post"] = None
    location: str = ""
    topic_ids: List[str] = field(default_factory=list)
    at_users: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Post":
        """Create Post instance from dictionary"""
        retweeted_status = None
        if data.get("retweeted_status"):
            retweeted_status = cls.from_dict(data["retweeted_status"])
        
        post_data = {
            "id": str(data.get("id", "")),
            "user_id": str(data.get("user_id", "")),
            "text": data.get("text", ""),
            "created_at": data.get("created_at"),
            "source": data.get("source", ""),
            "reposts_count": data.get("reposts_count", 0),
            "comments_count": data.get("comments_count", 0),
            "attitudes_count": data.get("attitudes_count", 0),
            "pic_urls": data.get("pic_urls", []),
            "video_url": data.get("video_url", ""),
            "is_original": data.get("is_original", True),
            "retweeted_status": retweeted_status,
            "location": data.get("location", ""),
            "topic_ids": data.get("topic_ids", []),
            "at_users": data.get("at_users", []),
            "raw_data": data,
        }
        return cls(**post_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Post instance to dictionary"""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "text": self.text,
            "created_at": self.created_at,
            "source": self.source,
            "reposts_count": self.reposts_count,
            "comments_count": self.comments_count,
            "attitudes_count": self.attitudes_count,
            "pic_urls": self.pic_urls,
            "video_url": self.video_url,
            "is_original": self.is_original,
            "location": self.location,
            "topic_ids": self.topic_ids,
            "at_users": self.at_users,
        }
        
        if self.retweeted_status:
            result["retweeted_status"] = self.retweeted_status.to_dict()
            
        return result