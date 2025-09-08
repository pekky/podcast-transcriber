#!/usr/bin/env python3
"""
Test script to demonstrate the interactive features of podcast_downloader.py
"""

from podcast_downloader import PodcastDownloader

def test_url_validation():
    """Test URL validation function"""
    downloader = PodcastDownloader()
    
    # Test valid URLs
    valid_urls = [
        "https://www.example.com/audio.mp3",
        "https://podcasts.apple.com/us/podcast/example/id123456789",
        "https://feeds.example.com/rss.xml"
    ]
    
    print("Testing URL validation:")
    for url in valid_urls:
        print(f"  {url}: {downloader.is_valid_url(url)}")

def test_filename_extraction():
    """Test filename extraction"""
    downloader = PodcastDownloader()
    
    test_urls = [
        "https://example.com/podcast_episode.mp3",
        "https://example.com/audio/episode123.m4a",
        "https://example.com/path/to/audio"
    ]
    
    print("\nTesting filename extraction:")
    for url in test_urls:
        filename = downloader.get_original_filename(url)
        print(f"  {url} -> {filename}")

if __name__ == "__main__":
    test_url_validation()
    test_filename_extraction()
    
    print("\n" + "="*50)
    print("Interactive features added to podcast_downloader.py:")
    print("1. 当没有提供URL参数时，会提示输入下载链接")
    print("2. 会验证URL的有效性，如果无效会要求重新输入") 
    print("3. 下载单个音频文件时会询问保存的文件名")
    print("4. 会显示原始文件名作为默认选项")
    print("\n使用方法:")
    print("  python podcast_downloader.py  # 交互式模式")
    print("  python podcast_downloader.py https://example.com/audio.mp3  # 直接模式")