from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class ShortVideoPlatform(Enum):
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"


@dataclass
class VideoModel:
    platform: ShortVideoPlatform
    video_id: Optional[str] = None
    author_name: Optional[str] = None
    unique_id: Optional[str] = None
    author_avatar: Optional[str] = None
    title: Optional[str] = None
    cover: Optional[str] = None
    video_url: Optional[str] = None
    mp3_url: Optional[str] = ""
    created_time: Optional[str] = None
    desc: Optional[str] = None
    duration: Optional[str] = None
    digg_count: Optional[int] = 0
    collect_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    share_count: Optional[int] = 0
    view_count: Optional[int] = 0
    share_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "video_id": self.video_id,
            "author_name": self.author_name,
            "unique_id": self.unique_id,
            "author_avatar": self.author_avatar,
            "title": self.title,
            "cover": self.cover,
            "video_url": self.video_url,
            "mp3_url": self.mp3_url,
            "created_time": self.created_time,
            "desc": self.desc,
            "duration": self.duration,
            "digg_count": self.digg_count,
            "collect_count": self.collect_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "view_count": self.view_count,
            "share_id": self.share_id,
        }


@dataclass
class AppConfig:
    name: str = "视频解析工具"
    tray_title: str = "视频解析工具"
    description: str = "视频解析工具是一个视频解析下载工具"
    download_path: str = ""
    repository_url: str = "https://github.com/YunLvCC/Video-parsing-tool"
    cookies: List[str] = field(default_factory=list)


@dataclass
class DownloadProgress:
    total_size: int = 0
    downloaded_size: int = 0
    speed: float = 0.0
    percentage: float = 0.0
    status: str = "pending"
