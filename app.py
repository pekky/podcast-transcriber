#!/usr/bin/env python3
"""
Podcast Transcriber Web Application
基于现有的 podcast_downloader.py 和 audio_transcriber.py 构建的 Web 应用
"""

import os
import uuid
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import logging

# 导入现有的转录器和下载器
from audio_transcriber import AudioTranscriber
from podcast_downloader import PodcastDownloader

app = Flask(__name__)
CORS(app)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = Path('static/uploads')
app.config['DOWNLOAD_FOLDER'] = Path('downloads')

# 创建必要的目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局任务状态存储
task_status = {}
task_results = {}

class WebTranscriber:
    """Web 应用的转录器封装类"""
    
    def __init__(self):
        self.downloader = PodcastDownloader()
        self.transcriber = AudioTranscriber()
    
    def download_audio(self, url: str, task_id: str) -> dict:
        """下载音频文件"""
        try:
            task_status[task_id] = {"status": "downloading", "progress": 0, "message": "开始下载..."}
            
            # 判断是否是 YouTube 链接
            if 'youtube.com' in url or 'youtu.be' in url:
                return self._download_youtube(url, task_id)
            else:
                return self._download_podcast(url, task_id)
                
        except Exception as e:
            logger.error(f"Download error for task {task_id}: {e}")
            task_status[task_id] = {"status": "error", "message": str(e)}
            return {"success": False, "error": str(e)}
    
    def _download_podcast(self, url: str, task_id: str) -> dict:
        """下载播客音频"""
        task_status[task_id]["message"] = "下载播客中..."
        
        # 使用现有的 podcast_downloader
        output_dir = app.config['DOWNLOAD_FOLDER']
        
        try:
            # 调用下载器 - 根据现有代码适配
            downloaded_files = self.downloader.download_single_episode(url, str(output_dir))
            
            if downloaded_files:
                audio_file = downloaded_files[0]  # 取第一个下载的文件
                
                # 转换为 MP3 格式（如果需要）
                mp3_file = self._convert_to_mp3(audio_file, task_id)
                
                task_status[task_id] = {"status": "completed", "progress": 100, "message": "下载完成"}
                
                return {
                    "success": True,
                    "audio_file": str(mp3_file),
                    "filename": Path(mp3_file).name,
                    "download_url": f"/download/{Path(mp3_file).name}"
                }
            else:
                raise Exception("下载失败，未获取到音频文件")
                
        except Exception as e:
            raise Exception(f"播客下载失败: {str(e)}")
    
    def _download_youtube(self, url: str, task_id: str) -> dict:
        """下载 YouTube 视频的音频"""
        try:
            import yt_dlp
        except ImportError:
            raise Exception("需要安装 yt-dlp: pip install yt-dlp")
        
        task_status[task_id]["message"] = "下载 YouTube 音频中..."
        
        output_dir = app.config['DOWNLOAD_FOLDER']
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"youtube_{timestamp}"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_dir / f'{output_filename}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # 查找生成的 MP3 文件
            mp3_file = output_dir / f'{output_filename}.mp3'
            if not mp3_file.exists():
                # 查找可能的其他格式文件
                for ext in ['.mp3', '.m4a', '.webm']:
                    potential_file = output_dir / f'{output_filename}{ext}'
                    if potential_file.exists():
                        mp3_file = potential_file
                        break
            
            if not mp3_file.exists():
                raise Exception("转换后的音频文件未找到")
            
            task_status[task_id] = {"status": "completed", "progress": 100, "message": "下载完成"}
            
            return {
                "success": True,
                "audio_file": str(mp3_file),
                "filename": mp3_file.name,
                "download_url": f"/download/{mp3_file.name}"
            }
            
        except Exception as e:
            raise Exception(f"YouTube 下载失败: {str(e)}")
    
    def _convert_to_mp3(self, audio_file: str, task_id: str) -> str:
        """转换音频文件为 MP3 格式"""
        audio_path = Path(audio_file)
        
        # 如果已经是 MP3，直接返回
        if audio_path.suffix.lower() == '.mp3':
            return str(audio_path)
        
        # 使用 pydub 转换为 MP3
        try:
            from pydub import AudioSegment
            
            task_status[task_id]["message"] = "转换为 MP3 格式中..."
            
            # 加载音频文件
            audio = AudioSegment.from_file(str(audio_path))
            
            # 生成 MP3 文件路径
            mp3_path = audio_path.with_suffix('.mp3')
            
            # 导出为 MP3
            audio.export(str(mp3_path), format="mp3", bitrate="192k")
            
            # 删除原文件（如果不是 MP3）
            if audio_path.exists() and audio_path != mp3_path:
                audio_path.unlink()
            
            return str(mp3_path)
            
        except ImportError:
            logger.warning("pydub 未安装，跳过音频格式转换")
            return str(audio_path)
        except Exception as e:
            logger.error(f"音频转换失败: {e}")
            return str(audio_path)
    
    def transcribe_audio(self, audio_file: str, task_id: str, with_speakers: bool = False) -> dict:
        """转录音频文件"""
        try:
            task_status[task_id] = {"status": "transcribing", "progress": 0, "message": "开始转录..."}
            
            audio_path = Path(audio_file)
            
            if not audio_path.exists():
                raise Exception(f"音频文件不存在: {audio_file}")
            
            # 使用现有的转录器
            if with_speakers:
                task_status[task_id]["message"] = "转录中（包含说话人识别）..."
                output_file = self.transcriber.transcribe_with_diarization(str(audio_path))
            else:
                task_status[task_id]["message"] = "转录中..."
                output_file = self.transcriber.transcribe_file(str(audio_path), format='txt')
            
            # 读取转录结果
            with open(output_file, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            
            task_status[task_id] = {"status": "completed", "progress": 100, "message": "转录完成"}
            
            return {
                "success": True,
                "transcript": transcript_text,
                "output_file": str(output_file),
                "filename": Path(output_file).name
            }
            
        except Exception as e:
            logger.error(f"Transcription error for task {task_id}: {e}")
            task_status[task_id] = {"status": "error", "message": str(e)}
            return {"success": False, "error": str(e)}

# 全局转录器实例
web_transcriber = WebTranscriber()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def download_audio():
    """下载音频 API"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"success": False, "error": "URL 不能为空"})
    
    # 生成任务 ID
    task_id = str(uuid.uuid4())
    
    # 在后台线程中处理下载
    thread = threading.Thread(
        target=lambda: task_results.update({task_id: web_transcriber.download_audio(url, task_id)})
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "task_id": task_id})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """转录音频 API"""
    data = request.get_json()
    audio_file = data.get('audio_file')
    with_speakers = data.get('with_speakers', False)
    
    if not audio_file:
        return jsonify({"success": False, "error": "音频文件路径不能为空"})
    
    # 生成任务 ID
    task_id = str(uuid.uuid4())
    
    # 在后台线程中处理转录
    thread = threading.Thread(
        target=lambda: task_results.update({
            task_id: web_transcriber.transcribe_audio(audio_file, task_id, with_speakers)
        })
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "task_id": task_id})

@app.route('/api/status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    status = task_status.get(task_id, {"status": "unknown", "message": "任务不存在"})
    result = task_results.get(task_id)
    
    response = {"status": status}
    if result:
        response["result"] = result
    
    return jsonify(response)

@app.route('/api/export/<task_id>')
def export_markdown(task_id):
    """导出为 Markdown 格式"""
    result = task_results.get(task_id)
    
    if not result or not result.get('success'):
        return jsonify({"success": False, "error": "任务结果不存在"})
    
    transcript = result.get('transcript', '')
    
    # 生成 Markdown 内容
    markdown_content = f"""# Podcast Transcript

**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Transcript

{transcript}

---

*Generated by Podcast Transcriber Web App*
"""
    
    # 保存 Markdown 文件
    filename = f"transcript_{task_id[:8]}.md"
    filepath = app.config['DOWNLOAD_FOLDER'] / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/download/<filename>')
def download_file(filename):
    """下载文件"""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("🚀 启动 Podcast Transcriber Web 应用...")
    print("📋 功能:")
    print("  - 支持 Podcast 和 YouTube 链接")
    print("  - 音频下载和 MP3 转换")
    print("  - 语音转录（可选说话人识别）")
    print("  - Markdown 格式导出")
    print("\n🌐 访问: http://localhost:8080")
    
    app.run(debug=True, host='0.0.0.0', port=8080)