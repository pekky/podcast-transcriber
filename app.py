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
import asyncio
import aiohttp
import json
import time

# 导入现有的转录器和下载器
from audio_transcriber import AudioTranscriber
from podcast_downloader import PodcastDownloader

# 导入词汇分析服务
try:
    from vocabulary_service import vocab_bp
    VOCAB_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"词汇分析服务不可用: {e}")
    VOCAB_SERVICE_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# 注册词汇分析蓝图
if VOCAB_SERVICE_AVAILABLE:
    app.register_blueprint(vocab_bp)
    print("✅ 词汇分析服务已启用")
else:
    print("⚠️  词汇分析服务未启用，将使用本地分析")

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
        """下载 YouTube 视频的音频 - 支持自动浏览器cookies"""
        try:
            import yt_dlp
        except ImportError:
            raise Exception("需要安装 yt-dlp: pip install yt-dlp")
        
        task_status[task_id]["message"] = "下载 YouTube 音频中..."
        
        output_dir = app.config['DOWNLOAD_FOLDER']
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"youtube_{timestamp}"
        
        # 尝试多个浏览器的cookies (按优先级)
        browsers_to_try = ['chrome', 'firefox', 'safari', 'edge', 'opera']
        
        for attempt, browser in enumerate(browsers_to_try):
            try:
                task_status[task_id]["message"] = f"尝试使用 {browser.title()} cookies 下载... ({attempt + 1}/{len(browsers_to_try)})"
                
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': str(output_dir / f'{output_filename}.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'cookiesfrombrowser': (browser, None, None, None),  # 自动从浏览器获取cookies
                }
                
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
                
                task_status[task_id] = {"status": "completed", "progress": 100, "message": f"下载完成 (使用 {browser.title()} cookies)"}
                
                return {
                    "success": True,
                    "audio_file": str(mp3_file),
                    "filename": mp3_file.name,
                    "download_url": f"/download/{mp3_file.name}"
                }
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 检查特定错误类型
                if "sign in" in error_msg or "not a bot" in error_msg or "cookies" in error_msg:
                    if attempt < len(browsers_to_try) - 1:
                        continue  # 尝试下一个浏览器
                elif "private" in error_msg or "unavailable" in error_msg:
                    raise Exception(f"视频私有或不可用: {str(e)}")
                elif "copyright" in error_msg:
                    raise Exception(f"版权限制: {str(e)}")  
                elif "region" in error_msg or "country" in error_msg:
                    raise Exception(f"地区限制: {str(e)}")
                elif "no such browser" in error_msg or "browser not found" in error_msg:
                    if attempt < len(browsers_to_try) - 1:
                        continue  # 尝试下一个浏览器
                else:
                    if attempt < len(browsers_to_try) - 1:
                        continue  # 尝试下一个浏览器
                
                # 如果是最后一次尝试，抛出错误
                if attempt == len(browsers_to_try) - 1:
                    raise Exception(f"所有浏览器cookies尝试失败。建议:\n1. 确保在浏览器中已登录YouTube\n2. 先在浏览器中访问该视频\n3. 检查视频是否为公开且无地区限制\n最终错误: {str(e)}")
        
        # 不应该到达这里，但为了安全起见
        raise Exception("未知错误: 所有下载尝试都失败了")
    
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
    
    def transcribe_audio(self, audio_file: str, task_id: str, with_speakers: bool = False, force_retranscribe: bool = False, output_format: str = 'txt') -> dict:
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
            task_status[task_id]["message"] = f"转录中{'（包含说话人识别）' if with_speakers else ''}，格式：{output_format.upper()}..."
            output_file = self.transcriber.transcribe_file(
                audio_path, 
                format=output_format,
                enable_diarization=with_speakers
            )
            
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
    output_format = data.get('output_format', 'txt')  # 输出格式，默认为txt
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
            task_id: web_transcriber.transcribe_audio(audio_file, task_id, with_speakers, force_retranscribe, output_format)
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

@app.route('/api/dictionary/<word>', methods=['GET'])
def get_word_definition(word):
    """
    获取单词的详细释义信息
    包括: 主要释义、例句、词根、同词根词汇、近义词
    """
    try:
        # 调用异步函数获取词典数据
        definition_data = asyncio.run(fetch_word_definition(word.lower()))
        
        if definition_data:
            return jsonify({
                'success': True,
                'word': word,
                'data': definition_data
            })
        else:
            return jsonify({
                'success': False,
                'word': word,
                'error': '未找到该单词的详细释义'
            })
            
    except Exception as e:
        print(f"❌ 获取单词 '{word}' 释义失败: {e}")
        return jsonify({
            'success': False,
            'word': word,
            'error': str(e)
        }), 500

async def fetch_word_definition(word):
    """
    异步获取单词的详细定义
    使用多个词典API源确保获取到完整信息
    """
    try:
        # 使用 Free Dictionary API 作为主要数据源
        primary_data = await fetch_from_free_dictionary(word)
        
        # 使用 WordsAPI 获取词根和相关词汇（如果需要）
        # words_api_data = await fetch_from_words_api(word)
        
        if primary_data:
            return primary_data
        else:
            # 如果主要API失败，返回基础信息
            return generate_fallback_definition(word)
            
    except Exception as e:
        print(f"❌ 异步获取词典数据失败: {e}")
        return generate_fallback_definition(word)

async def fetch_from_free_dictionary(word):
    """
    从 Free Dictionary API 获取词汇信息
    """
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and len(data) > 0:
                        entry = data[0]
                        
                        # 提取所有释义
                        definitions = []
                        examples = []
                        synonyms = set()
                        
                        for meaning in entry.get('meanings', []):
                            part_of_speech = meaning.get('partOfSpeech', '')
                            
                            for definition in meaning.get('definitions', []):
                                def_text = definition.get('definition', '')
                                example = definition.get('example', '')
                                
                                if def_text:
                                    definitions.append({
                                        'partOfSpeech': part_of_speech,
                                        'definition': def_text,
                                        'example': example
                                    })
                                
                                if example:
                                    examples.append(example)
                                
                                # 收集近义词
                                for syn in definition.get('synonyms', []):
                                    synonyms.add(syn)
                        
                        # 获取发音
                        phonetics = []
                        for phonetic in entry.get('phonetics', []):
                            if phonetic.get('text'):
                                phonetics.append(phonetic.get('text'))
                        
                        # 词根分析（简化版）
                        etymology = extract_word_etymology(word)
                        
                        return {
                            'word': word,
                            'phonetics': phonetics,
                            'definitions': definitions[:8],  # 限制数量
                            'examples': examples[:5],
                            'synonyms': list(synonyms)[:8],
                            'etymology': etymology,
                            'related_words': generate_related_words(word),
                            'source': 'Free Dictionary API'
                        }
                
                return None
                
    except Exception as e:
        print(f"❌ Free Dictionary API 请求失败: {e}")
        return None

def extract_word_etymology(word):
    """
    简化的词根分析
    """
    # 常见词根映射
    common_roots = {
        'dict': {'meaning': '说、讲', 'examples': ['dictate', 'predict', 'verdict']},
        'spect': {'meaning': '看', 'examples': ['inspect', 'respect', 'prospect']},
        'port': {'meaning': '携带', 'examples': ['transport', 'import', 'export']},
        'form': {'meaning': '形状', 'examples': ['inform', 'transform', 'conform']},
        'graph': {'meaning': '写', 'examples': ['photograph', 'telegraph', 'autograph']},
        'struct': {'meaning': '建造', 'examples': ['construct', 'destruct', 'instruct']},
        'tract': {'meaning': '拉', 'examples': ['attract', 'contract', 'extract']},
        'press': {'meaning': '压', 'examples': ['compress', 'express', 'suppress']},
        'ject': {'meaning': '投掷', 'examples': ['project', 'reject', 'inject']},
        'miss': {'meaning': '发送', 'examples': ['mission', 'transmit', 'dismiss']},
        'mit': {'meaning': '发送', 'examples': ['commit', 'permit', 'submit']},
        'act': {'meaning': '行动', 'examples': ['action', 'react', 'interact']},
        'inter': {'meaning': '在...之间', 'examples': ['international', 'interview', 'internet']},
        'auto': {'meaning': '自动', 'examples': ['automatic', 'automobile', 'autobiography']},
        'bio': {'meaning': '生命', 'examples': ['biology', 'biography', 'antibiotic']},
        'geo': {'meaning': '地球', 'examples': ['geography', 'geology', 'geometry']},
        'tele': {'meaning': '远距离', 'examples': ['telephone', 'television', 'telescope']},
        'micro': {'meaning': '微小', 'examples': ['microscope', 'microwave', 'microphone']},
        'macro': {'meaning': '大', 'examples': ['macroscope', 'macroeconomics', 'macrocosm']},
        'poly': {'meaning': '多', 'examples': ['polygon', 'polymath', 'polymer']},
        'mono': {'meaning': '单一', 'examples': ['monopoly', 'monologue', 'monotone']},
        'multi': {'meaning': '多', 'examples': ['multiple', 'multimedia', 'multinational']},
        'uni': {'meaning': '一', 'examples': ['university', 'uniform', 'unique']},
        'bi': {'meaning': '二', 'examples': ['bicycle', 'bilingual', 'binary']},
        'tri': {'meaning': '三', 'examples': ['triangle', 'tricycle', 'triple']},
        'pre': {'meaning': '之前', 'examples': ['predict', 'prepare', 'prevent']},
        'post': {'meaning': '之后', 'examples': ['postpone', 'postgraduate', 'postwar']},
        'anti': {'meaning': '反对', 'examples': ['antibody', 'antisocial', 'antibiotic']},
        'pro': {'meaning': '支持', 'examples': ['progress', 'promote', 'protect']},
        'con': {'meaning': '一起', 'examples': ['connect', 'contribute', 'conference']},
        'de': {'meaning': '相反', 'examples': ['decrease', 'destroy', 'develop']},
        're': {'meaning': '重新', 'examples': ['return', 'repeat', 'review']},
        'un': {'meaning': '不', 'examples': ['unhappy', 'unknown', 'unusual']},
        'dis': {'meaning': '不', 'examples': ['disagree', 'disappear', 'disconnect']},
        'mis': {'meaning': '错误', 'examples': ['mistake', 'misunderstand', 'mislead']},
        'over': {'meaning': '过度', 'examples': ['overcome', 'overflow', 'overlook']},
        'under': {'meaning': '不足', 'examples': ['understand', 'underground', 'underestimate']},
        'super': {'meaning': '超过', 'examples': ['superior', 'supernatural', 'supervise']},
        'sub': {'meaning': '在下面', 'examples': ['submarine', 'subway', 'substitute']},
        'trans': {'meaning': '跨越', 'examples': ['transport', 'translate', 'transform']},
        'ex': {'meaning': '出', 'examples': ['export', 'exit', 'example']},
        'in': {'meaning': '进入', 'examples': ['import', 'input', 'include']},
        'extra': {'meaning': '额外', 'examples': ['extraordinary', 'extract', 'extreme']},
        'intra': {'meaning': '内部', 'examples': ['intranet', 'intramural', 'intravenous']},
        'circum': {'meaning': '周围', 'examples': ['circumference', 'circumstance', 'circumnavigate']},
        'per': {'meaning': '通过', 'examples': ['perfect', 'perform', 'permit']},
        'para': {'meaning': '旁边', 'examples': ['parallel', 'paragraph', 'parameter']},
        'meta': {'meaning': '超越', 'examples': ['metaphor', 'metabolism', 'metamorphosis']},
        'hyper': {'meaning': '超过', 'examples': ['hyperactive', 'hyperlink', 'hyperbole']},
        'hypo': {'meaning': '在下面', 'examples': ['hypothesis', 'hypoglycemia', 'hypodermic']},
        'semi': {'meaning': '半', 'examples': ['semicircle', 'semifinal', 'semiconductor']},
        'quasi': {'meaning': '类似', 'examples': ['quasi-official', 'quasi-legal', 'quasi-scientific']},
        'pseudo': {'meaning': '假的', 'examples': ['pseudonym', 'pseudo-science', 'pseudo-code']},
        'neo': {'meaning': '新的', 'examples': ['neonatal', 'neoclassical', 'neologism']},
        'retro': {'meaning': '向后', 'examples': ['retrospective', 'retroactive', 'retrofit']},
        'ultra': {'meaning': '极度', 'examples': ['ultraviolet', 'ultrasound', 'ultra-modern']},
        'mega': {'meaning': '巨大', 'examples': ['megabyte', 'megaphone', 'megalopolis']},
        'mini': {'meaning': '小', 'examples': ['minimum', 'miniature', 'minimize']},
        'maxi': {'meaning': '最大', 'examples': ['maximum', 'maximize', 'maximal']},
        'omni': {'meaning': '全部', 'examples': ['omnipresent', 'omnipotent', 'omnivore']},
        'pan': {'meaning': '全部', 'examples': ['pandemic', 'panorama', 'panacea']},
        'mal': {'meaning': '坏', 'examples': ['malfunction', 'malicious', 'malpractice']},
        'ben': {'meaning': '好', 'examples': ['benefit', 'benevolent', 'beneficial']},
        'eu': {'meaning': '好', 'examples': ['euphemism', 'euphoria', 'euthanasia']},
        'dys': {'meaning': '困难', 'examples': ['dysfunction', 'dyslexia', 'dystopia']},
        'homo': {'meaning': '相同', 'examples': ['homogeneous', 'homosexual', 'homophone']},
        'hetero': {'meaning': '不同', 'examples': ['heterosexual', 'heterogeneous', 'heterodox']},
        'iso': {'meaning': '相等', 'examples': ['isometric', 'isotope', 'isosceles']},
        'equi': {'meaning': '相等', 'examples': ['equivalent', 'equilibrium', 'equidistant']},
        'co': {'meaning': '一起', 'examples': ['cooperate', 'coordinate', 'collaborate']},
        'syn': {'meaning': '一起', 'examples': ['synchronize', 'synthesis', 'synonym']},
        'sym': {'meaning': '一起', 'examples': ['symbol', 'symmetry', 'symphony']},
        'ana': {'meaning': '向上', 'examples': ['analysis', 'anatomy', 'analogy']},
        'cata': {'meaning': '向下', 'examples': ['catastrophe', 'catalyst', 'category']},
        'dia': {'meaning': '通过', 'examples': ['dialogue', 'diameter', 'diagnosis']},
        'epi': {'meaning': '在上面', 'examples': ['epidemic', 'episode', 'epilogue']},
        'apo': {'meaning': '离开', 'examples': ['apology', 'apostle', 'apocalypse']},
        'endo': {'meaning': '内部', 'examples': ['endocrine', 'endoscope', 'endogenous']},
        'exo': {'meaning': '外部', 'examples': ['exotic', 'exodus', 'exoskeleton']},
        'thermo': {'meaning': '热', 'examples': ['thermometer', 'thermostat', 'thermal']},
        'hydro': {'meaning': '水', 'examples': ['hydrogen', 'hydraulic', 'hydration']},
        'pneumo': {'meaning': '空气', 'examples': ['pneumonia', 'pneumatic', 'pneumonia']},
        'cardio': {'meaning': '心脏', 'examples': ['cardiology', 'cardiovascular', 'cardiac']},
        'neuro': {'meaning': '神经', 'examples': ['neurology', 'neuroscience', 'neurotic']},
        'psycho': {'meaning': '心理', 'examples': ['psychology', 'psychotic', 'psychotherapy']},
        'socio': {'meaning': '社会', 'examples': ['sociology', 'socioeconomic', 'societal']},
        'photo': {'meaning': '光', 'examples': ['photograph', 'photosynthesis', 'photon']},
        'chrono': {'meaning': '时间', 'examples': ['chronology', 'chronic', 'synchronize']},
        'logo': {'meaning': '词语', 'examples': ['dialogue', 'apology', 'biology']},
        'phil': {'meaning': '爱', 'examples': ['philosophy', 'philanthropist', 'philology']},
        'phobia': {'meaning': '恐惧', 'examples': ['claustrophobia', 'arachnophobia', 'xenophobia']},
        'phile': {'meaning': '爱好者', 'examples': ['bibliophile', 'audiophile', 'francophile']},
        'cracy': {'meaning': '统治', 'examples': ['democracy', 'autocracy', 'bureaucracy']},
        'archy': {'meaning': '统治', 'examples': ['monarchy', 'hierarchy', 'anarchy']},
        'ism': {'meaning': '主义', 'examples': ['capitalism', 'socialism', 'nationalism']},
        'ist': {'meaning': '主义者', 'examples': ['capitalist', 'socialist', 'nationalist']},
        'ology': {'meaning': '学科', 'examples': ['biology', 'psychology', 'sociology']},
        'ography': {'meaning': '记录', 'examples': ['biography', 'geography', 'photography']},
        'metry': {'meaning': '测量', 'examples': ['geometry', 'symmetry', 'telemetry']},
        'scopy': {'meaning': '观察', 'examples': ['microscopy', 'telescope', 'horoscope']},
        'therapy': {'meaning': '治疗', 'examples': ['psychotherapy', 'physiotherapy', 'chemotherapy']},
        'pathic': {'meaning': '感受', 'examples': ['empathic', 'telepathic', 'sympathetic']},
        'genic': {'meaning': '产生', 'examples': ['photogenic', 'allergenic', 'carcinogenic']},
        'phobic': {'meaning': '恐惧的', 'examples': ['claustrophobic', 'hydrophobic', 'xenophobic']},
        'philic': {'meaning': '喜爱的', 'examples': ['hydrophilic', 'bibliophilic', 'thermophilic']},
        'static': {'meaning': '静止的', 'examples': ['hydrostatic', 'electrostatic', 'homeostatic']},
        'kinetic': {'meaning': '运动的', 'examples': ['kinetic', 'telekinetic', 'psychokinetic']},
        'tropic': {'meaning': '转向的', 'examples': ['phototropic', 'geotropic', 'heliotropic']},
        'morphic': {'meaning': '形状的', 'examples': ['polymorphic', 'anthropomorphic', 'metamorphic']},
        'centric': {'meaning': '中心的', 'examples': ['eccentric', 'concentric', 'geocentric']},
        'gamous': {'meaning': '婚姻的', 'examples': ['monogamous', 'polygamous', 'bigamous']},
        'vorous': {'meaning': '吃的', 'examples': ['carnivorous', 'herbivorous', 'omnivorous']},
        'ferous': {'meaning': '带有的', 'examples': ['coniferous', 'carboniferous', 'metalliferous']},
        'genous': {'meaning': '产生的', 'examples': ['homogeneous', 'heterogeneous', 'indigenous']},
        'logous': {'meaning': '相似的', 'examples': ['analogous', 'homologous', 'tautologous']},
        'nomial': {'meaning': '名字的', 'examples': ['binomial', 'polynomial', 'monomial']},
        'somal': {'meaning': '身体的', 'examples': ['chromosomal', 'ribosomal', 'autosomal']},
        'tomy': {'meaning': '切割', 'examples': ['anatomy', 'lobotomy', 'appendectomy']},
        'ectomy': {'meaning': '切除', 'examples': ['appendectomy', 'tonsillectomy', 'mastectomy']},
        'ostomy': {'meaning': '造口', 'examples': ['colostomy', 'tracheostomy', 'ileostomy']},
        'plasty': {'meaning': '重建', 'examples': ['rhinoplasty', 'angioplasty', 'arthroplasty']},
        'osis': {'meaning': '状态', 'examples': ['diagnosis', 'prognosis', 'neurosis']},
        'itis': {'meaning': '炎症', 'examples': ['arthritis', 'hepatitis', 'bronchitis']},
        'algia': {'meaning': '疼痛', 'examples': ['neuralgia', 'nostalgia', 'myalgia']},
        'emia': {'meaning': '血液状态', 'examples': ['anemia', 'leukemia', 'glycemia']},
        'uria': {'meaning': '尿液状态', 'examples': ['dysuria', 'polyuria', 'hematuria']},
        'pathy': {'meaning': '疾病', 'examples': ['neuropathy', 'empathy', 'telepathy']},
        'philia': {'meaning': '喜爱', 'examples': ['bibliophilia', 'hemophilia', 'necrophilia']},
        'phage': {'meaning': '吃', 'examples': ['bacteriophage', 'macrophage', 'anthropophage']},
        'cide': {'meaning': '杀', 'examples': ['suicide', 'homicide', 'pesticide']},
        'stat': {'meaning': '停止', 'examples': ['thermostat', 'hemostat', 'rheostat']},
        'troph': {'meaning': '营养', 'examples': ['atrophy', 'dystrophy', 'hypertrophy']},
        'trophy': {'meaning': '营养', 'examples': ['atrophy', 'dystrophy', 'hypertrophy']},
        'plasm': {'meaning': '形成', 'examples': ['cytoplasm', 'protoplasm', 'neoplasm']},
        'blast': {'meaning': '胚芽', 'examples': ['fibroblast', 'osteoblast', 'neuroblast']},
        'clast': {'meaning': '破坏', 'examples': ['osteoclast', 'iconoclast', 'pyroclast']},
        'cyte': {'meaning': '细胞', 'examples': ['leukocyte', 'erythrocyte', 'lymphocyte']},
        'soma': {'meaning': '身体', 'examples': ['chromosome', 'ribosome', 'autosome']},
        'zoon': {'meaning': '动物', 'examples': ['protozoon', 'metazoon', 'spermatozoon']},
        'phyte': {'meaning': '植物', 'examples': ['epiphyte', 'saprophyte', 'neophyte']},
        'derm': {'meaning': '皮肤', 'examples': ['epidermis', 'hypodermic', 'dermatology']},
        'carp': {'meaning': '果实', 'examples': ['pericarp', 'endocarp', 'mesocarp']},
        'sperm': {'meaning': '种子', 'examples': ['angiosperm', 'gymnosperm', 'endosperm']},
        'phyll': {'meaning': '叶子', 'examples': ['chlorophyll', 'xanthophyll', 'mesophyll']},
        'flor': {'meaning': '花', 'examples': ['florist', 'flora', 'floriculture']},
        'arbor': {'meaning': '树', 'examples': ['arboreal', 'arboretum', 'arboriculture']},
        'herbi': {'meaning': '草', 'examples': ['herbivore', 'herbicide', 'herbarium']},
        'sylv': {'meaning': '森林', 'examples': ['sylvan', 'Pennsylvania', 'silviculture']},
        'aqua': {'meaning': '水', 'examples': ['aquarium', 'aquatic', 'aqueduct']},
        'mare': {'meaning': '海', 'examples': ['marine', 'maritime', 'submarine']},
        'terra': {'meaning': '土地', 'examples': ['territory', 'terrain', 'terrestrial']},
        'geo': {'meaning': '地球', 'examples': ['geography', 'geology', 'geometry']},
        'cosm': {'meaning': '宇宙', 'examples': ['cosmos', 'cosmology', 'microcosm']},
        'astro': {'meaning': '星', 'examples': ['astronomy', 'astronaut', 'astrology']},
        'helio': {'meaning': '太阳', 'examples': ['heliocentric', 'heliotrope', 'helium']},
        'luna': {'meaning': '月亮', 'examples': ['lunar', 'lunatic', 'lunation']},
        'stella': {'meaning': '星', 'examples': ['stellar', 'constellation', 'interstellar']},
        'meteor': {'meaning': '流星', 'examples': ['meteorology', 'meteorite', 'meteor']},
        'aero': {'meaning': '空气', 'examples': ['aeronautics', 'aerobic', 'aerospace']},
        'atmo': {'meaning': '大气', 'examples': ['atmosphere', 'atmospheric', 'atmometer']},
        'baro': {'meaning': '压力', 'examples': ['barometer', 'barometric', 'isobar']},
        'hygro': {'meaning': '湿度', 'examples': ['hygrometer', 'hygroscopic', 'hygrophyte']},
        'cryo': {'meaning': '冷', 'examples': ['cryogenic', 'cryosurgery', 'cryosphere']},
        'pyrO': {'meaning': '火', 'examples': ['pyromania', 'pyroclastic', 'pyrotechnics']},
        'igni': {'meaning': '火', 'examples': ['ignite', 'ignition', 'igneous']},
        'calor': {'meaning': '热', 'examples': ['calorie', 'calorimeter', 'caloric']},
        'frigi': {'meaning': '冷', 'examples': ['frigid', 'refrigerate', 'frigidarium']},
        'gelo': {'meaning': '冰', 'examples': ['congelation', 'gelid', 'gelato']},
        'niv': {'meaning': '雪', 'examples': ['niveous', 'nival', 'connivent']},
        'pluvi': {'meaning': '雨', 'examples': ['pluvial', 'pluviometer', 'pluvious']},
        'nimb': {'meaning': '云', 'examples': ['nimbus', 'cumulonimbus', 'nimbostratus']},
        'vent': {'meaning': '风', 'examples': ['ventilation', 'ventilate', 'adventure']},
        'spir': {'meaning': '呼吸', 'examples': ['inspire', 'perspire', 'respiratory']},
        'pneum': {'meaning': '肺', 'examples': ['pneumonia', 'pneumatic', 'pneumothorax']},
        'pulmo': {'meaning': '肺', 'examples': ['pulmonary', 'pulmonic', 'cardiopulmonary']},
        'rhin': {'meaning': '鼻', 'examples': ['rhinoceros', 'rhinitis', 'rhinoplasty']},
        'nas': {'meaning': '鼻', 'examples': ['nasal', 'nasopharynx', 'prenatal']},
        'ot': {'meaning': '耳', 'examples': ['otology', 'otitis', 'otoscope']},
        'audi': {'meaning': '听', 'examples': ['audio', 'auditorium', 'audible']},
        'phon': {'meaning': '声音', 'examples': ['telephone', 'phonetics', 'symphony']},
        'son': {'meaning': '声音', 'examples': ['sonic', 'resonance', 'dissonance']},
        'opt': {'meaning': '眼', 'examples': ['optic', 'optical', 'optometrist']},
        'ocul': {'meaning': '眼', 'examples': ['ocular', 'binocular', 'oculomotor']},
        'ophthalm': {'meaning': '眼', 'examples': ['ophthalmology', 'ophthalmic', 'ophthalmoscope']},
        'vis': {'meaning': '看', 'examples': ['vision', 'visual', 'invisible']},
        'vid': {'meaning': '看', 'examples': ['video', 'evidence', 'provide']},
        'scop': {'meaning': '看', 'examples': ['telescope', 'microscope', 'horoscope']},
        'spec': {'meaning': '看', 'examples': ['inspect', 'spectacle', 'respect']},
        'spic': {'meaning': '看', 'examples': ['conspicuous', 'auspicious', 'perspicacious']},
        'luc': {'meaning': '光', 'examples': ['lucid', 'translucent', 'elucidate']},
        'lumin': {'meaning': '光', 'examples': ['luminous', 'illuminate', 'luminary']},
        'clar': {'meaning': '清楚', 'examples': ['clarify', 'declare', 'clear']},
        'manifest': {'meaning': '显示', 'examples': ['manifest', 'manifesto', 'manifestation']},
        'demonstr': {'meaning': '显示', 'examples': ['demonstrate', 'demonstrative', 'demonstration']},
        'monstr': {'meaning': '显示', 'examples': ['monster', 'demonstrate', 'remonstrate']},
        'ostent': {'meaning': '显示', 'examples': ['ostentatious', 'ostentation', 'ostensible']},
        'apparent': {'meaning': '显然', 'examples': ['apparent', 'transparency', 'apparition']},
        'evident': {'meaning': '明显', 'examples': ['evident', 'evidence', 'evidential']},
        'obvious': {'meaning': '明显', 'examples': ['obvious', 'obviousness', 'obviously']},
        'patent': {'meaning': '明显', 'examples': ['patent', 'patently', 'patentee']},
        'flagr': {'meaning': '燃烧', 'examples': ['flagrant', 'conflagration', 'deflagration']},
        'fulg': {'meaning': '闪光', 'examples': ['fulgent', 'effulgent', 'refulgent']},
        'corrus': {'meaning': '闪光', 'examples': ['coruscate', 'coruscating', 'coruscation']},
        'scintill': {'meaning': '闪烁', 'examples': ['scintillate', 'scintillating', 'scintillation']},
        'radi': {'meaning': '光线', 'examples': ['radio', 'radiate', 'radiation']},
        'ray': {'meaning': '光线', 'examples': ['ray', 'array', 'disarray']}
    }
    
    # 检查词汇中是否包含已知词根
    for root, info in common_roots.items():
        if root in word:
            return {
                'root': root,
                'meaning': info['meaning'],
                'examples': info['examples']
            }
    
    return None

def generate_related_words(word):
    """
    生成相关词汇（基于简单的形态学规则）
    """
    related = []
    
    # 基于后缀生成相关词
    if word.endswith('ion'):
        base = word[:-3]
        related.extend([f"{base}e", f"{base}ing", f"{base}ed"])
    elif word.endswith('ly'):
        base = word[:-2]
        related.extend([base, f"{base}ness"])
    elif word.endswith('ing'):
        base = word[:-3]
        related.extend([base, f"{base}ed", f"{base}er"])
    elif word.endswith('ed'):
        base = word[:-2]
        related.extend([base, f"{base}ing", f"{base}er"])
    elif word.endswith('er'):
        base = word[:-2]
        related.extend([base, f"{base}ing", f"{base}ed"])
    
    return list(set(related))[:5]  # 去重并限制数量

def generate_fallback_definition(word):
    """
    生成后备定义（当API调用失败时）
    """
    return {
        'word': word,
        'phonetics': [f'/{word}/'],
        'definitions': [{
            'partOfSpeech': 'unknown',
            'definition': f'{word}的释义（词典API暂不可用）',
            'example': ''
        }],
        'examples': [],
        'synonyms': [],
        'etymology': None,
        'related_words': generate_related_words(word),
        'source': 'Fallback'
    }

if __name__ == '__main__':
    print("🚀 启动 Podcast Transcriber Web 应用...")
    print("📋 功能:")
    print("  - 支持 Podcast 和 YouTube 链接")
    print("  - 音频下载和 MP3 转换")
    print("  - 语音转录（可选说话人识别）")
    print("  - Markdown 格式导出")
    print("\n🌐 访问: http://localhost:8081")
    
    app.run(debug=True, host='0.0.0.0', port=8081)