#!/usr/bin/env python3
"""
Test script to demonstrate the interactive features of audio_transcriber.py
"""

from audio_transcriber import AudioTranscriber
from pathlib import Path

def test_file_listing():
    """Test audio file listing functionality"""
    transcriber = AudioTranscriber()
    
    # List files in downloads directory
    audio_files = transcriber.list_audio_files(Path("downloads"))
    
    print("Testing file listing functionality:")
    print("=" * 50)
    print(f"Found {len(audio_files)} audio files in downloads directory:")
    
    for i, file_path in enumerate(audio_files, 1):
        file_size = transcriber.get_file_size_mb(file_path)
        duration_info = transcriber._get_duration_info(file_path)
        
        print(f"{i:2d}. {file_path.name}")
        print(f"    大小: {file_size:.1f} MB{duration_info}")
        print(f"    格式: {file_path.suffix.upper()}")
        print()

def demonstrate_supported_formats():
    """Demonstrate supported formats"""
    transcriber = AudioTranscriber()
    
    print("\nSupported audio formats:")
    print("=" * 50)
    supported_formats = ['.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.wma']
    
    for fmt in supported_formats:
        print(f"✓ {fmt.upper()} format")
    
    print("\nFormat detection:")
    downloads_dir = Path("downloads")
    if downloads_dir.exists():
        for file_path in downloads_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                print(f"  {file_path.name} -> {file_path.suffix.upper()} format detected")

if __name__ == "__main__":
    print("🎤 Audio Transcriber Interactive Features Demo")
    print("=" * 60)
    
    test_file_listing()
    demonstrate_supported_formats()
    
    print("\n" + "=" * 60)
    print("Interactive features added to audio_transcriber.py:")
    print("1. 当没有提供文件参数时，会列出downloads目录下的所有音频文件")
    print("2. 显示文件大小、时长和路径信息")
    print("3. 支持交互式选择要转录的文件")
    print("4. 支持 MP3 和 M4A 等多种音频格式")
    print("5. 提供文件编号选择和退出选项")
    print("\n使用方法:")
    print("  python3 audio_transcriber.py  # 交互式选择模式")
    print("  python3 audio_transcriber.py audio.mp3  # 直接指定文件模式")