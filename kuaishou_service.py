import re
import json
import logging
from typing import Optional
from datetime import datetime

import requests

from models import VideoModel, ShortVideoPlatform


class KuaiShouService:
    LOCATION_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

    def extract_url(self, text: str) -> str:
        self.logger.info(f"开始解析快手链接: {text}")
        match = re.search(r'https?://[^\s]+', text, re.IGNORECASE)
        return match.group(0) if match else ""

    def preprocess_url(self, url: str) -> str:
        if "v.kuaishou.com" in url or "kuaishou.com" in url or "chenzhongtech.com" in url:
            try:
                response = self.session.head(
                    url, 
                    headers=self.LOCATION_HEADERS, 
                    allow_redirects=True, 
                    timeout=5
                )
                url = response.url
            except Exception as e:
                self.logger.warning(f"预处理短链接失败: {e}")
        
        if not url.startswith("http"):
            url = "https://" + url
        
        return url

    def extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'/short-video/([a-zA-Z0-9_-]+)',
            r'/photo/([a-zA-Z0-9_-]+)',
            r'/fw/photo/([a-zA-Z0-9_-]+)',
            r'photoId=([a-zA-Z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def parse_video_data(self, text: str) -> Optional[VideoModel]:
        try:
            self.logger.info(f"开始解析快手链接: {text}")
            
            url = self.extract_url(text)
            if not url:
                raise ValueError("未找到有效的链接")
            
            url = self.preprocess_url(url)
            self.logger.info(f"预处理后的链接: {url}")
            
            video_id = self.extract_video_id(url)
            if not video_id:
                raise ValueError("无法从链接中提取视频ID")
            
            self.logger.info(f"视频ID: {video_id}")
            
            api_url = f"https://m.gifshow.com/fw/photo/{video_id}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cookie": "kpf=PC_WEB; clientid=3; did=web_5ee38d442bc5387e413eeeefc42ed4a2; didv=1734437469000; kpn=KUAISHOU_VISION",
            }
            
            response = self.session.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            content = response.text
            
            if not content:
                raise ValueError("响应内容为空")
            
            self.logger.debug(f"响应内容长度: {len(content)}")
            
            photo_pattern = r'"photo":\s*\{(.*?)\},\s*"serialInfo"'
            match = re.search(photo_pattern, content, re.DOTALL)
            
            if match:
                self.logger.info("使用photo模式解析")
                video_json = "{" + match.group(1) + "}"
                video_data = json.loads(video_json)
                
                main_mv_urls = video_data.get("mainMvUrls", [])
                cover_urls = video_data.get("coverUrls", [])
                
                video_url = main_mv_urls[0].get("url") if main_mv_urls else None
                cover_url = cover_urls[0].get("url") if cover_urls else None
                
                timestamp = video_data.get("timestamp", 0)
                created_time_str = ""
                if timestamp:
                    try:
                        created_time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        created_time_str = str(timestamp)
                
                return VideoModel(
                    platform=ShortVideoPlatform.KUAISHOU,
                    video_id=video_data.get("manifest", {}).get("videoId"),
                    author_name=video_data.get("userName"),
                    unique_id=video_data.get("manifest", {}).get("videoId"),
                    author_avatar=str(video_data.get("headUrl")) if video_data.get("headUrl") else None,
                    title=video_data.get("caption"),
                    cover=str(cover_url) if cover_url else None,
                    video_url=str(video_url) if video_url else None,
                    mp3_url="",
                    created_time=created_time_str,
                    desc=video_data.get("caption"),
                    duration=str(video_data.get("duration", 0)),
                    digg_count=video_data.get("likeCount", 0),
                    collect_count=0,
                    comment_count=video_data.get("commentCount", 0),
                    share_count=video_data.get("shareCount", 0),
                    view_count=video_data.get("viewCount", 0),
                )
            
            initial_state_pattern = r'window\.INIT_STATE\s*=\s*(\{.*?\})\s*</script>'
            match = re.search(initial_state_pattern, content, re.DOTALL)
            
            if match:
                self.logger.info("使用INIT_STATE模式解析")
                init_data = json.loads(match.group(1))
                
                for key, value in init_data.items():
                    if 'photo' in key.lower() and isinstance(value, dict):
                        photo_data = value
                        if 'photo' in photo_data:
                            photo = photo_data['photo']
                            
                            main_mv_urls = photo.get("mainMvUrls", [])
                            cover_urls = photo.get("coverUrls", [])
                            
                            video_url = main_mv_urls[0].get("url") if main_mv_urls else None
                            cover_url = cover_urls[0].get("url") if cover_urls else None
                            
                            author = photo.get("author", {})
                            
                            timestamp = photo.get("timestamp", 0)
                            created_time_str = ""
                            if timestamp:
                                try:
                                    created_time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
                                except:
                                    created_time_str = str(timestamp)
                            
                            return VideoModel(
                                platform=ShortVideoPlatform.KUAISHOU,
                                video_id=photo.get("photoId"),
                                author_name=author.get("name") or author.get("userName"),
                                unique_id=author.get("id"),
                                author_avatar=author.get("headerUrl"),
                                title=photo.get("caption"),
                                cover=cover_url,
                                video_url=video_url,
                                mp3_url="",
                                created_time=created_time_str,
                                desc=photo.get("caption"),
                                duration="",
                                digg_count=photo.get("likeCount", 0),
                                collect_count=0,
                                comment_count=photo.get("commentCount", 0),
                                share_count=0,
                                view_count=photo.get("viewCount", 0),
                            )
            
            raise ValueError("未匹配到视频数据")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {e}")
            raise ValueError(f"JSON解析错误: {e}")
        except requests.RequestException as e:
            self.logger.error(f"网络请求错误: {e}")
            raise ValueError(f"网络请求错误: {e}")
        except Exception as e:
            self.logger.error(f"解析快手视频失败: {e}")
            raise
