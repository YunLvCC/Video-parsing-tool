import os
import logging
import time
from typing import Callable, Optional
from dataclasses import dataclass

import requests

from models import DownloadProgress


@dataclass
class DownloadResult:
    success: bool
    file_path: str = ""
    error_message: str = ""


class DownloaderService:
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cancel_flag = False

    def cancel(self):
        self._cancel_flag = True

    def download(
        self,
        url: str,
        save_path: str,
        file_name: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        chunk_size: int = 8192,
        timeout: int = 30,
        max_retries: int = 3
    ) -> DownloadResult:
        self._cancel_flag = False
        
        full_path = os.path.join(save_path, file_name)
        os.makedirs(save_path, exist_ok=True)
        
        headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "*/*",
        }
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"开始下载: {url} (尝试 {attempt + 1}/{max_retries})")
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    stream=True, 
                    timeout=timeout
                )
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                start_time = time.time()
                
                progress = DownloadProgress(
                    total_size=total_size,
                    downloaded_size=0,
                    speed=0.0,
                    percentage=0.0,
                    status="downloading"
                )
                
                if progress_callback:
                    progress_callback(progress)
                
                with open(full_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if self._cancel_flag:
                            self.logger.info("下载已取消")
                            if os.path.exists(full_path):
                                os.remove(full_path)
                            return DownloadResult(
                                success=False,
                                error_message="下载已取消"
                            )
                        
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            elapsed_time = time.time() - start_time
                            speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                            
                            progress = DownloadProgress(
                                total_size=total_size,
                                downloaded_size=downloaded_size,
                                speed=speed,
                                percentage=(downloaded_size / total_size * 100) if total_size > 0 else 0,
                                status="downloading"
                            )
                            
                            if progress_callback:
                                progress_callback(progress)
                
                progress = DownloadProgress(
                    total_size=total_size,
                    downloaded_size=downloaded_size,
                    speed=0.0,
                    percentage=100.0,
                    status="completed"
                )
                
                if progress_callback:
                    progress_callback(progress)
                
                self.logger.info(f"下载完成: {full_path}")
                return DownloadResult(success=True, file_path=full_path)
                
            except requests.RequestException as e:
                self.logger.error(f"下载失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    if os.path.exists(full_path):
                        os.remove(full_path)
                    return DownloadResult(
                        success=False,
                        error_message=f"下载失败: {str(e)}"
                    )
            except Exception as e:
                self.logger.error(f"下载出错: {e}")
                if os.path.exists(full_path):
                    os.remove(full_path)
                return DownloadResult(
                    success=False,
                    error_message=f"下载出错: {str(e)}"
                )
        
        return DownloadResult(success=False, error_message="下载失败")

    @staticmethod
    def format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def format_speed(speed_bytes: float) -> str:
        if speed_bytes < 1024:
            return f"{speed_bytes:.2f} B/s"
        elif speed_bytes < 1024 * 1024:
            return f"{speed_bytes / 1024:.2f} KB/s"
        else:
            return f"{speed_bytes / (1024 * 1024):.2f} MB/s"
