import sys
import os
import logging
import threading
import webbrowser
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

from models import VideoModel, ShortVideoPlatform, AppConfig, DownloadProgress
from douyin_service import DouYinService
from kuaishou_service import KuaiShouService
from downloader import DownloaderService, DownloadResult


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('short_video_downloader.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class ParseThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.douyin_service = DouYinService()
        self.kuaishou_service = KuaiShouService()
    
    def run(self):
        try:
            url = self.url.strip()
            
            if "douyin" in url.lower():
                video_model = self.douyin_service.parse_video_data(url)
            elif "kuaishou" in url.lower():
                video_model = self.kuaishou_service.parse_video_data(url)
            else:
                self.error.emit("暂不支持该平台的链接")
                return
            
            if video_model:
                self.finished.emit(video_model)
            else:
                self.error.emit("解析失败，请检查链接是否正确")
        except Exception as e:
            self.error.emit(f"解析失败: {str(e)}")


class DownloadThread(QThread):
    progress = pyqtSignal(object)
    finished = pyqtSignal(object)
    
    def __init__(self, url: str, save_path: str, file_name: str):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.file_name = file_name
        self.downloader = DownloaderService()
    
    def run(self):
        def progress_callback(progress: DownloadProgress):
            self.progress.emit(progress)
        
        result = self.downloader.download(
            self.url,
            self.save_path,
            self.file_name,
            progress_callback
        )
        self.finished.emit(result)
    
    def cancel(self):
        self.downloader.cancel()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.video_model: Optional[VideoModel] = None
        self.parse_thread: Optional[ParseThread] = None
        self.download_thread: Optional[DownloadThread] = None
        
        self.config = AppConfig()
        if not self.config.download_path:
            self.config.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("视频解析工具")
        self.setMinimumSize(700, 750)
        self.resize(700, 750)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        url_group = QGroupBox("链接输入")
        url_layout = QHBoxLayout(url_group)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入抖音或快手分享链接...")
        self.url_input.setMinimumHeight(36)
        url_layout.addWidget(self.url_input)
        
        self.parse_btn = QPushButton("解析")
        self.parse_btn.setMinimumWidth(80)
        self.parse_btn.setMinimumHeight(36)
        self.parse_btn.clicked.connect(self.parse_url)
        url_layout.addWidget(self.parse_btn)
        
        main_layout.addWidget(url_group)
        
        info_group = QGroupBox("视频信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(440)
        self.info_text.setPlaceholderText("解析后显示视频信息...")
        info_layout.addWidget(self.info_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.play_btn = QPushButton("播放视频")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_video)
        btn_layout.addWidget(self.play_btn)
        
        self.open_cover_btn = QPushButton("查看封面")
        self.open_cover_btn.setEnabled(False)
        self.open_cover_btn.clicked.connect(self.open_cover)
        btn_layout.addWidget(self.open_cover_btn)
        
        btn_layout.addStretch()
        
        info_layout.addLayout(btn_layout)
        main_layout.addWidget(info_group)
        
        download_group = QGroupBox("下载设置")
        download_layout = QGridLayout(download_group)
        
        download_layout.addWidget(QLabel("保存路径:"), 0, 0)
        
        self.path_input = QLineEdit()
        self.path_input.setText(self.config.download_path)
        self.path_input.setMinimumHeight(32)
        download_layout.addWidget(self.path_input, 0, 1)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMinimumWidth(80)
        self.browse_btn.clicked.connect(self.browse_path)
        download_layout.addWidget(self.browse_btn, 0, 2)
        
        download_layout.addWidget(QLabel("文件名:"), 1, 0)
        
        self.filename_input = QLineEdit()
        self.filename_input.setMinimumHeight(32)
        self.filename_input.setPlaceholderText("自动生成文件名")
        download_layout.addWidget(self.filename_input, 1, 1, 1, 2)
        
        main_layout.addWidget(download_group)
        
        progress_group = QGroupBox("下载进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m KB")
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)
        
        btn_layout2 = QHBoxLayout()
        btn_layout2.addStretch()
        
        self.download_btn = QPushButton("下载视频")
        self.download_btn.setMinimumWidth(120)
        self.download_btn.setMinimumHeight(40)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_video)
        btn_layout2.addWidget(self.download_btn)
        
        btn_layout2.addStretch()
        main_layout.addLayout(btn_layout2)
        
        self.apply_styles()
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
    
    def parse_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入视频链接")
            return
        
        self.parse_btn.setEnabled(False)
        self.info_text.clear()
        self.info_text.setPlaceholderText("正在解析...")
        
        self.parse_thread = ParseThread(url)
        self.parse_thread.finished.connect(self.on_parse_finished)
        self.parse_thread.error.connect(self.on_parse_error)
        self.parse_thread.start()
    
    def on_parse_finished(self, video_model: VideoModel):
        self.video_model = video_model
        self.parse_btn.setEnabled(True)
        
        platform_name = "抖音" if video_model.platform == ShortVideoPlatform.DOUYIN else "快手"
        
        info_text = f"平台: {platform_name}\n"
        info_text += f"作者: {video_model.author_name or '未知'}\n"
        info_text += f"作者ID: {video_model.unique_id or '未知'}\n"
        info_text += f"标题: {video_model.title or '无'}\n"
        info_text += f"描述: {video_model.desc or '无'}\n"
        info_text += f"点赞数: {video_model.digg_count or 0}\n"
        info_text += f"评论数: {video_model.comment_count or 0}\n"
        info_text += f"分享数: {video_model.share_count or 0}\n"
        info_text += f"创建时间: {video_model.created_time or '未知'}\n"
        
        self.info_text.setText(info_text)
        
        if video_model.video_url:
            video_title = video_model.desc or video_model.title or "video"
            video_title = video_title[:50] if len(video_title) > 50 else video_title
            default_filename = f"{video_title}.mp4"
            default_filename = self.sanitize_filename(default_filename)
            self.filename_input.setText(default_filename)
        
        self.play_btn.setEnabled(bool(video_model.video_url))
        self.open_cover_btn.setEnabled(bool(video_model.cover))
        self.download_btn.setEnabled(bool(video_model.video_url))
    
    def on_parse_error(self, error_msg: str):
        self.parse_btn.setEnabled(True)
        self.info_text.setPlaceholderText("解析失败")
        QMessageBox.critical(self, "错误", error_msg)
    
    def sanitize_filename(self, filename: str) -> str:
        invalid_chars = '<>:"/\\|?*\n\r\t'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        filename = filename.strip()
        while '  ' in filename:
            filename = filename.replace('  ', ' ')
        return filename
    
    def play_video(self):
        if self.video_model and self.video_model.video_url:
            webbrowser.open(self.video_model.video_url)
    
    def open_cover(self):
        if self.video_model and self.video_model.cover:
            webbrowser.open(self.video_model.cover)
    
    def browse_path(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "选择保存路径",
            self.path_input.text()
        )
        if path:
            self.path_input.setText(path)
    
    def download_video(self):
        if not self.video_model or not self.video_model.video_url:
            QMessageBox.warning(self, "警告", "请先解析视频链接")
            return
        
        save_path = self.path_input.text().strip()
        if not save_path:
            QMessageBox.warning(self, "警告", "请选择保存路径")
            return
        
        file_name = self.filename_input.text().strip()
        if not file_name:
            video_title = self.video_model.desc or self.video_model.title or "video"
            video_title = video_title[:50] if len(video_title) > 50 else video_title
            file_name = self.sanitize_filename(video_title) + ".mp4"
        
        if not file_name.endswith('.mp4'):
            file_name += '.mp4'
        
        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在下载...")
        
        self.download_thread = DownloadThread(
            self.video_model.video_url,
            save_path,
            file_name
        )
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()
    
    def on_download_progress(self, progress: DownloadProgress):
        if progress.total_size > 0:
            self.progress_bar.setMaximum(int(progress.total_size / 1024))
            self.progress_bar.setValue(int(progress.downloaded_size / 1024))
        
        speed_str = DownloaderService.format_speed(progress.speed)
        self.status_label.setText(f"下载中... {speed_str}")
    
    def on_download_finished(self, result: DownloadResult):
        self.download_btn.setEnabled(True)
        
        if result.success:
            self.status_label.setText("下载完成!")
        else:
            self.status_label.setText(f"下载失败: {result.error_message}")
            QMessageBox.critical(self, "错误", result.error_message)
    
    def closeEvent(self, event):
        if self.parse_thread and self.parse_thread.isRunning():
            self.parse_thread.terminate()
            self.parse_thread.wait()
        
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait()
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.setWindowIcon(app.windowIcon())
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
