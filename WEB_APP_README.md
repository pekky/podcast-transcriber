# 🎙️ Podcast Transcriber Web 应用

一个基于 Flask 的现代化 Web 应用，支持 Podcast 和 YouTube 音频的下载、转录和导出。

## ✨ 功能特性

### 🔗 多平台支持
- **Podcast 链接**: Apple Podcasts、RSS 订阅源
- **YouTube 视频**: 自动提取音频
- **音频格式**: 自动转换为 MP3 格式

### 🎯 智能转录
- **OpenAI Whisper**: 高质量语音识别
- **说话人识别**: 可选的多人对话区分
- **实时进度**: 转录进度实时显示

### 📄 导出功能
- **Markdown 格式**: 带时间戳的转录文档
- **文件下载**: 音频和转录文件直接下载
- **在线预览**: 页面内转录结果显示

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础依赖（如果还未安装）
pip3 install -r requirements.txt

# Web 应用额外依赖
pip3 install -r web_requirements.txt
```

### 2. 启动应用

```bash
python3 app.py
```

### 3. 访问界面

打开浏览器访问: **http://localhost:8080**

## 🎯 使用流程

### 步骤 1: 输入链接
1. 在左侧面板输入 Podcast 或 YouTube 链接
2. 点击下载按钮 📥

### 步骤 2: 等待下载
- 应用会自动识别链接类型
- 显示下载进度
- 自动转换为 MP3 格式

### 步骤 3: 开始转录
1. 选择是否需要说话人识别
2. 点击"开始转录"按钮
3. 等待转录完成

### 步骤 4: 查看结果
- 转录文本显示在右侧面板
- 支持 Markdown 格式导出
- 可以下载音频文件

## 📁 项目结构

```
podcast-transcriber/
├── app.py                          # Flask 主应用
├── audio_transcriber.py            # 音频转录器
├── podcast_downloader.py           # 播客下载器
├── vocabulary_analyzer.py          # 词汇分析器
├── templates/
│   └── index.html                  # 主页模板
├── static/
│   ├── css/style.css              # 样式文件
│   ├── js/main.js                 # 前端逻辑
│   └── uploads/                   # 临时文件
├── downloads/                      # 下载的音频文件
└── requirements.txt               # 项目依赖
```

## 🔧 技术架构

### 后端技术
- **Flask 3.1.2**: Web 框架
- **Flask-CORS**: 跨域请求支持
- **OpenAI Whisper**: 语音识别
- **pyannote.audio**: 说话人识别
- **yt-dlp**: YouTube 视频下载

### 前端技术
- **Bootstrap 5.1.3**: UI 框架
- **Font Awesome 6.0**: 图标库
- **Vanilla JavaScript**: 前端逻辑

## 🌟 Web 应用特色功能

### 1. 实时任务状态
- 后台任务处理
- 实时进度更新
- 状态指示器

### 2. 响应式设计
- 移动端适配
- 现代化 UI 设计
- 流畅的用户体验

### 3. 错误处理
- 友好的错误提示
- 自动重试机制
- 详细的日志记录

### 4. 文件管理
- 自动文件清理
- 安全的文件访问
- 多格式支持

## 📱 API 接口

### POST /api/download
下载音频文件

**请求体**:
```json
{
  "url": "https://example.com/podcast"
}
```

**响应**:
```json
{
  "success": true,
  "task_id": "uuid"
}
```

### POST /api/transcribe
转录音频

**请求体**:
```json
{
  "audio_file": "/path/to/audio.mp3",
  "with_speakers": true
}
```

### GET /api/status/{task_id}
获取任务状态

### GET /api/export/{task_id}
导出 Markdown 文件

## ⚙️ 配置选项

### 环境变量
```bash
# Hugging Face Token（说话人识别）
export HF_TOKEN=your_token_here

# 最大文件大小（默认 500MB）
export MAX_CONTENT_LENGTH=524288000
```

### Flask 配置
- **DEBUG**: 开发模式（默认开启）
- **HOST**: 监听地址（默认 0.0.0.0）
- **PORT**: 监听端口（默认 8080）

## 🔒 安全注意事项

1. **生产部署**: 使用 WSGI 服务器（如 Gunicorn）
2. **文件权限**: 确保上传目录权限正确
3. **网络安全**: 配置防火墙和 HTTPS
4. **资源限制**: 设置合理的文件大小限制

## 🎛️ 高级配置

### 异步任务处理
生产环境建议使用 Celery + Redis：

```bash
pip3 install celery redis
```

### 音频格式支持
安装 FFmpeg 支持更多音频格式：

```bash
# macOS
brew install ffmpeg

# Ubuntu
apt-get install ffmpeg
```

## 🐛 常见问题

### 1. 端口被占用
```bash
# 修改 app.py 中的端口
app.run(debug=True, host='0.0.0.0', port=8081)
```

### 2. Whisper 模型下载缓慢
```bash
# 设置镜像源
export HF_ENDPOINT=https://hf-mirror.com
```

### 3. 说话人识别失败
- 确保 HF_TOKEN 已设置
- 检查 Hugging Face 模型访问权限

## 🚀 部署建议

### 开发环境
```bash
python3 app.py
```

### 生产环境
```bash
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

### Docker 部署
```dockerfile
FROM python:3.9

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN pip install -r web_requirements.txt

EXPOSE 8080

CMD ["python3", "app.py"]
```

## 📊 性能优化

1. **模型缓存**: Whisper 模型自动缓存
2. **文件清理**: 定期清理临时文件
3. **并发处理**: 多线程任务处理
4. **资源监控**: 监控内存和 CPU 使用

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

## 📄 许可证

MIT License

---

**🎉 享受使用 Podcast Transcriber Web 应用！**

如有问题或建议，欢迎提交 Issue 或 Pull Request。