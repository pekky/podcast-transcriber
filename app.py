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
        self.downloader = PodcastDownloader(str(app.config['DOWNLOAD_FOLDER']))
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
            # 获取下载前的文件列表
            files_before = set(os.listdir(str(output_dir))) if output_dir.exists() else set()
            
            # 调用下载器
            self.downloader.download_from_url(url, max_episodes=1)
            
            # 获取下载后的文件列表
            files_after = set(os.listdir(str(output_dir))) if output_dir.exists() else set()
            
            # 找到新下载的文件
            new_files = list(files_after - files_before)
            
            if new_files:
                # 选择最新的音频文件
                audio_files = [f for f in new_files if f.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.ogg', '.mp4'))]
                if audio_files:
                    audio_file = str(output_dir / audio_files[0])
                    
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
                    raise Exception("下载的文件中没有找到音频文件")
            else:
                raise Exception("下载失败，未获取到新文件")
                
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
    
    def backup_existing_transcript(self, audio_path: Path) -> None:
        """备份已存在的转录文件"""
        try:
            audio_stem = audio_path.stem
            possible_transcript_files = [
                audio_path.parent / f"{audio_stem}.txt",
                audio_path.parent / f"{audio_stem}_speakers.txt",
                audio_path.parent / f"{audio_stem}_transcript.txt"
            ]
            
            for transcript_path in possible_transcript_files:
                if transcript_path.exists():
                    # 生成备份文件名：原名_old_日期时间
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_name = f"{transcript_path.stem}_old_{timestamp}{transcript_path.suffix}"
                    backup_path = transcript_path.parent / backup_name
                    
                    # 重命名原文件
                    transcript_path.rename(backup_path)
                    logger.info(f"Backed up transcript: {transcript_path} -> {backup_path}")
                    
        except Exception as e:
            logger.warning(f"Failed to backup transcript files: {e}")
    
    def transcribe_audio(self, audio_file: str, task_id: str, with_speakers: bool = False, force_retranscribe: bool = False) -> dict:
        """转录音频文件"""
        try:
            task_status[task_id] = {"status": "transcribing", "progress": 0, "message": "开始转录..."}
            
            audio_path = Path(audio_file)
            
            if not audio_path.exists():
                raise Exception(f"音频文件不存在: {audio_file}")
            
            # 如果是强制重新转录，备份现有转录文件
            if force_retranscribe:
                self.backup_existing_transcript(audio_path)
            
            # 使用现有的转录器
            if with_speakers:
                task_status[task_id]["message"] = "转录中（包含说话人识别）..."
                output_file = self.transcriber.transcribe_with_diarization(audio_path)
            else:
                task_status[task_id]["message"] = "转录中..."
                output_file = self.transcriber.transcribe_file(audio_path, format='txt')
            
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
    selected_file = data.get('selected_file')  # 从选择器选择的文件
    with_speakers = data.get('with_speakers', False)
    force_retranscribe = data.get('force_retranscribe', False)  # 是否强制重新转录
    
    # 优先使用选择的文件，否则使用之前下载的文件路径
    if selected_file:
        # 确保选择的文件在downloads目录内（安全检查）
        download_folder = app.config['DOWNLOAD_FOLDER']
        selected_path = Path(selected_file)
        
        # 检查路径是否安全（防止路径遍历攻击）
        if not selected_path.name == selected_file or '/' in selected_file or '\\' in selected_file:
            return jsonify({"success": False, "error": "无效的文件路径"})
            
        audio_file_path = download_folder / selected_file
        
        if not audio_file_path.exists():
            return jsonify({"success": False, "error": "选择的音频文件不存在"})
            
        audio_file = str(audio_file_path)
        
    elif not audio_file:
        return jsonify({"success": False, "error": "请选择音频文件或提供音频文件路径"})
    
    # 生成任务 ID
    task_id = str(uuid.uuid4())
    
    # 在后台线程中处理转录
    thread = threading.Thread(
        target=lambda: task_results.update({
            task_id: web_transcriber.transcribe_audio(audio_file, task_id, with_speakers, force_retranscribe)
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

@app.route('/api/audio-files')
def list_audio_files():
    """获取已下载的音频文件列表"""
    try:
        download_folder = app.config['DOWNLOAD_FOLDER']
        if not download_folder.exists():
            return jsonify({"success": True, "files": []})
        
        audio_extensions = ('.mp3', '.m4a', '.wav', '.flac', '.ogg', '.mp4', '.aac', '.wma')
        audio_files = []
        
        for file_path in download_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                # 获取文件信息
                file_stat = file_path.stat()
                file_info = {
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    "download_url": f"/download/{file_path.name}"
                }
                audio_files.append(file_info)
        
        # 按修改时间排序（最新的在前）
        audio_files.sort(key=lambda x: x["modified"], reverse=True)
        
        return jsonify({"success": True, "files": audio_files})
        
    except Exception as e:
        logger.error(f"Error listing audio files: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/transcript/<filename>')
def get_existing_transcript(filename):
    """获取已存在的转录文件"""
    try:
        download_folder = app.config['DOWNLOAD_FOLDER']
        audio_file_path = download_folder / filename
        
        if not audio_file_path.exists():
            return jsonify({"success": False, "error": "音频文件不存在"})
        
        # 查找对应的转录文件
        audio_stem = audio_file_path.stem
        possible_transcript_files = [
            download_folder / f"{audio_stem}.txt",
            download_folder / f"{audio_stem}_speakers.txt",
            download_folder / f"{audio_stem}_transcript.txt",
            download_folder / f"{audio_stem}_merged.txt",
            # 也在项目根目录查找（因为转录器可能在根目录生成文件）
            Path(f"{audio_stem}.txt"),
            Path(f"{audio_stem}_speakers.txt"),
            Path(f"{audio_stem}_transcript.txt"),
            Path(f"{audio_stem}_merged.txt")
        ]
        
        transcript_file = None
        transcript_content = None
        
        # 查找最新的转录文件
        for transcript_path in possible_transcript_files:
            if transcript_path.exists():
                transcript_file = transcript_path
                break
        
        if transcript_file:
            try:
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                
                file_stat = transcript_file.stat()
                return jsonify({
                    "success": True,
                    "exists": True,
                    "transcript": transcript_content,
                    "transcript_file": str(transcript_file),
                    "created": datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.error(f"Error reading transcript file {transcript_file}: {e}")
                return jsonify({
                    "success": True,
                    "exists": True,
                    "transcript": f"错误：无法读取转录文件 - {str(e)}",
                    "transcript_file": str(transcript_file),
                    "created": "未知"
                })
        else:
            return jsonify({"success": True, "exists": False})
            
    except Exception as e:
        logger.error(f"Error checking transcript for {filename}: {e}")
        return jsonify({"success": False, "error": str(e)})

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