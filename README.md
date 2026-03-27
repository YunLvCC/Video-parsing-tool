# 视频解析工具

一个用于解析和下载抖音、快手视频的Python桌面应用程序。

## 功能特性

- 支持抖音短视频解析和下载
- 支持快手短视频解析和下载
- 自动识别分享链接
- 显示视频详细信息（作者、标题、点赞数等）
- 支持自定义下载路径和文件名
- 下载进度显示
- 现代化GUI界面

## 系统要求

- Python 3.8+
- Windows / macOS / Linux

## 安装和运行

### 方式一：使用启动脚本（Windows）

双击运行 `run.bat`，脚本会自动：

1. 创建Python虚拟环境
2. 安装所需依赖
3. 启动程序

### 方式二：手动安装

```bash
# 进入项目目录
cd python_version

# 创建虚拟环境（可选）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

## 项目结构

```
python_version/
├── main.py              # 主程序入口和GUI界面
├── models.py            # 数据模型定义
├── douyin_service.py    # 抖音解析服务
├── kuaishou_service.py  # 快手解析服务
├── downloader.py        # 下载服务
├── config.json          # 配置文件
├── requirements.txt     # Python依赖
├── run.bat              # Windows启动脚本
└── README.md            # 说明文档
```

## 使用方法

1. 打开程序
2. 将抖音或快手的分享链接粘贴到输入框
3. 点击"解析"按钮
4. 查看解析出的视频信息
5. 选择保存路径和文件名
6. 点击"下载视频"开始下载

## 支持的链接格式

### 抖音

- `https://v.douyin.com/xxx/` (短链接)
- `https://www.douyin.com/video/xxx` (完整链接)

### 快手

- `https://www.kuaishou.com/short-video/xxx`
- `https://v.kuaishou.com/xxx` (短链接)

## 技术栈

- **GUI框架**: PyQt6
- **HTTP请求**: requests
- **日志**: logging

## 注意事项

1. 请确保网络连接正常
2. 部分视频可能因为隐私设置无法解析
3. 下载的视频仅供个人学习使用，请勿用于商业用途
4. 尊重原作者版权，下载后请勿二次传播

## 许可证

MIT License
