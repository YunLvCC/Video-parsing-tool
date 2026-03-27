import re
import json
import logging
from typing import Optional
from datetime import datetime

import requests

from models import VideoModel, ShortVideoPlatform


class DouYinService:
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "sec-ch-ua-platform": "Windows",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        "referer": "https://www.douyin.com/?recommend=1",
        "priority": "u=1, i",
        "pragma": "no-cache",
        "cache-control": "no-cache",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "dnt": "1"
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    def extract_url(self, text: str) -> str:
        self.logger.info(f"开始解析抖音链接: {text}")
        match = re.search(r'https?://[^\s]+', text, re.IGNORECASE)
        return match.group(0) if match else ""

    def preprocess_url(self, url: str) -> str:
        if "v.douyin.com" in url or "iesdouyin.com" in url:
            try:
                response = self.session.head(url, allow_redirects=True, timeout=5)
                url = response.url
            except Exception as e:
                self.logger.warning(f"预处理短链接失败: {e}")
        
        if not url.startswith("http"):
            url = "https://" + url
        
        return url

    def parse_video_data(self, text: str) -> Optional[VideoModel]:
        try:
            self.logger.info(f"开始解析抖音链接: {text}")
            
            url = self.extract_url(text)
            if not url:
                raise ValueError("未找到有效的链接")
            
            url = self.preprocess_url(url)
            self.logger.info(f"预处理后的链接: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            content = response.text
            
            if not content:
                raise ValueError("响应内容为空")
            
            self.logger.debug(f"响应内容长度: {len(content)}")
            
            video_model = self._try_parse_router_data(content)
            if video_model:
                return video_model
            
            video_model = self._try_parse_item_list(content)
            if video_model:
                return video_model
            
            video_model = self._try_parse_aweme_list(content)
            if video_model:
                return video_model
            
            video_model = self._try_parse_play_addr(content)
            if video_model:
                return video_model
            
            raise ValueError("未匹配到视频数据，所有解析模式均失败")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {e}")
            raise ValueError(f"JSON解析错误: {e}")
        except requests.RequestException as e:
            self.logger.error(f"网络请求错误: {e}")
            raise ValueError(f"网络请求错误: {e}")
        except Exception as e:
            self.logger.error(f"解析抖音视频失败: {e}")
            raise

    def _try_parse_router_data(self, content: str) -> Optional[VideoModel]:
        try:
            pattern = r'_ROUTER_DATA\s*=\s*(\{.*?\})<'
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                return None
            
            self.logger.info("使用_ROUTER_DATA模式解析")
            video_json = match.group(1)
            video_data = json.loads(video_json)
            
            loader_data = video_data.get("loaderData", {})
            video_id_page = (
                loader_data.get("video_(id)/page", {}) or 
                loader_data.get("videoIdPage", {})
            )
            video_info_res = video_id_page.get("videoInfoRes", {})
            item_list = video_info_res.get("item_list", []) or video_info_res.get("itemList", [])
            
            if not item_list:
                return None
            
            return self._build_video_model(item_list[0])
        except Exception as e:
            self.logger.warning(f"_ROUTER_DATA模式解析失败: {e}")
            return None

    def _try_parse_item_list(self, content: str) -> Optional[VideoModel]:
        try:
            pattern = r'itemList\s*:\s*\[(.*?)\](?:\s*[,}]|\s*$)'
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                return None
            
            self.logger.info("使用itemList模式解析")
            video_json = "[" + match.group(1) + "]"
            video_list = json.loads(video_json)
            
            if not video_list:
                return None
            
            return self._build_video_model(video_list[0])
        except Exception as e:
            self.logger.warning(f"itemList模式解析失败: {e}")
            return None

    def _try_parse_aweme_list(self, content: str) -> Optional[VideoModel]:
        try:
            pattern = r'awemeList\s*:\s*\[(.*?)\](?:\s*[,}]|\s*$)'
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                return None
            
            self.logger.info("使用awemeList模式解析")
            video_json = "[" + match.group(1) + "]"
            video_list = json.loads(video_json)
            
            if not video_list:
                return None
            
            return self._build_video_model(video_list[0])
        except Exception as e:
            self.logger.warning(f"awemeList模式解析失败: {e}")
            return None

    def _try_parse_play_addr(self, content: str) -> Optional[VideoModel]:
        try:
            pattern = r'playAddr\s*:\s*\{(.*?)\}(?:\s*[,}]|\s*$)'
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                return None
            
            self.logger.info("使用playAddr模式解析")
            playaddr_json = "{" + match.group(1) + "}"
            playaddr_data = json.loads(playaddr_json)
            
            url_list = playaddr_data.get("urlList", [])
            if not url_list:
                return None
            
            video_url = url_list[0].replace("playwm", "play")
            
            return VideoModel(
                platform=ShortVideoPlatform.DOUYIN,
                video_url=video_url,
            )
        except Exception as e:
            self.logger.warning(f"playAddr模式解析失败: {e}")
            return None

    def _build_video_model(self, video_info: dict) -> VideoModel:
        author = video_info.get("author", {})
        video = video_info.get("video", {})
        statistics = video_info.get("statistics", {})
        
        play_addr = video.get("play_addr", {}) or video.get("playAddr", {})
        cover = video.get("cover", {})
        
        video_url = ""
        aweme_type = video_info.get("aweme_type", 0) or video_info.get("awemeType", 0)
        
        if aweme_type == 2:
            url_list = cover.get("url_list", []) or cover.get("urlList", [])
            video_url = url_list[0] if url_list else ""
        else:
            url_list = play_addr.get("url_list", []) or play_addr.get("urlList", [])
            if url_list:
                video_url = url_list[0].replace("playwm", "play")
        
        avatar_thumb = author.get("avatar_thumb", {}) or author.get("avatarThumb", {})
        avatar_url_list = avatar_thumb.get("url_list", []) or avatar_thumb.get("urlList", [])
        
        cover_url_list = cover.get("url_list", []) or cover.get("urlList", [])
        
        create_time = video_info.get("create_time", 0) or video_info.get("createTime", 0)
        created_time_str = ""
        if create_time:
            try:
                created_time_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S")
            except:
                created_time_str = str(create_time)
        
        unique_id = author.get("unique_id", "") or author.get("uniqueId", "") or author.get("short_id", "") or author.get("shortId", "")
        
        digg_count = statistics.get("digg_count", 0) or statistics.get("diggCount", 0)
        collect_count = statistics.get("collect_count", 0) or statistics.get("collectCount", 0)
        comment_count = statistics.get("comment_count", 0) or statistics.get("commentCount", 0)
        share_count = statistics.get("share_count", 0) or statistics.get("shareCount", 0)
        
        return VideoModel(
            platform=ShortVideoPlatform.DOUYIN,
            video_id=video_info.get("aweme_id") or video_info.get("awemeId"),
            author_name=author.get("nickname"),
            unique_id=unique_id,
            author_avatar=avatar_url_list[0] if avatar_url_list else None,
            title=author.get("signature"),
            cover=cover_url_list[-1] if cover_url_list else None,
            video_url=video_url,
            mp3_url="",
            created_time=created_time_str,
            desc=video_info.get("desc"),
            duration="",
            digg_count=digg_count,
            collect_count=collect_count,
            comment_count=comment_count,
            share_count=share_count,
        )
