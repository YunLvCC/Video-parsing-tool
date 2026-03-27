"""
视频解析工具 - 支持抖音和快手视频解析下载
"""

__version__ = "1.0.0"
__author__ = "YunLvCC"

from .models import VideoModel, ShortVideoPlatform, AppConfig, DownloadProgress
from .douyin_service import DouYinService
from .kuaishou_service import KuaiShouService
from .downloader import DownloaderService
