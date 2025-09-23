#!/usr/bin/env python3
"""
Podcast Audio Downloader

This script downloads audio files from podcast URLs and saves them locally.
Supports both direct audio file URLs and RSS feed URLs.
"""

import os
import sys
import requests
import urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
import argparse
import re
import json
import time
import urllib.request
from urllib.error import URLError, HTTPError

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    print("⚠️  yt-dlp not available. YouTube downloading will be disabled.")
    print("Install with: pip install yt-dlp")


class PodcastDownloader:
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.apple_itunes_api = "https://itunes.apple.com/lookup"

    def is_audio_url(self, url: str) -> bool:
        """Check if URL points to an audio file."""
        audio_extensions = ('.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.wma')
        parsed = urllib.parse.urlparse(url)
        return any(parsed.path.lower().endswith(ext) for ext in audio_extensions)

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and reachable."""
        try:
            # Basic URL format check
            parsed = urllib.parse.urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False
            
            # Try to access the URL (head request to avoid downloading)
            response = self.session.head(url, allow_redirects=True, timeout=10)
            return response.status_code < 400
        except Exception:
            return False

    def get_original_filename(self, url: str) -> str:
        """Extract original filename from URL."""
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path) or "podcast_audio"
        
        # Remove extension to get base name
        if '.' in filename:
            base_name = os.path.splitext(filename)[0]
        else:
            base_name = filename
            
        return base_name

    def get_custom_filename(self, original_filename: str) -> str:
        """Prompt user for custom filename with original as default."""
        while True:
            custom_name = input(f"请输入保存的文件名 (默认: {original_filename}): ").strip()
            
            if not custom_name:
                return original_filename
            
            # Clean filename to avoid filesystem issues
            clean_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
            if clean_name:
                return clean_name
            else:
                print("✗ 文件名无效，请重新输入")

    def download_audio_file(self, url: str, filename: Optional[str] = None, ask_filename: bool = True) -> bool:
        """Download audio file from direct URL."""
        try:
            # Handle potential authentication requirements
            response = self.session.get(url, stream=True, allow_redirects=True)
            
            # Check for authentication challenges
            if response.status_code == 401:
                print(f"✗ Authentication required for {url}")
                print("💡 Try using --cookies with your browser's cookies file")
                return False
            elif response.status_code == 403:
                print(f"✗ Access forbidden for {url}")
                print("💡 Content may require subscription or have geographic restrictions")
                return False
            
            response.raise_for_status()
            
            if not filename:
                original_filename = self.get_original_filename(url)
                if ask_filename:
                    base_filename = self.get_custom_filename(original_filename)
                else:
                    base_filename = original_filename
                filename = base_filename
            
            # Ensure filename has an extension
            if '.' not in filename:
                content_type = response.headers.get('content-type', '')
                if 'audio/mpeg' in content_type or 'audio/mp3' in content_type:
                    filename += '.mp3'
                elif 'audio/mp4' in content_type or 'audio/m4a' in content_type:
                    filename += '.m4a'
                else:
                    filename += '.mp3'  # default
            
            filepath = self.output_dir / filename
            
            print(f"Downloading: {filename}")
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"✓ Saved to: {filepath}")
            return True
            
        except Exception as e:
            print(f"✗ Error downloading {url}: {e}")
            if "404" in str(e):
                print("💡 The audio file may no longer be available")
            elif "403" in str(e):
                print("💡 Access may require authentication or subscription")
            return False

    def parse_rss_feed(self, url: str) -> List[Dict[str, str]]:
        """Parse RSS feed and extract podcast episodes."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            episodes = []
            
            # Find all item elements (episodes)
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                enclosure_elem = item.find('enclosure')
                
                if enclosure_elem is not None:
                    audio_url = enclosure_elem.get('url')
                    if audio_url:
                        title = title_elem.text if title_elem is not None else "Unknown Episode"
                        # Clean title for filename
                        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                        episodes.append({
                            'title': title,
                            'url': audio_url,
                            'filename': f"{clean_title}.mp3"
                        })
            
            return episodes
            
        except Exception as e:
            print(f"✗ Error parsing RSS feed: {e}")
            return []

    def is_apple_podcast_url(self, url: str) -> bool:
        """Check if URL is from Apple Podcasts."""
        return 'podcasts.apple.com' in url
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is from YouTube."""
        youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com', 'www.youtube.com']
        return any(domain in url.lower() for domain in youtube_domains)
    
    def extract_podcast_id(self, apple_url: str) -> Optional[str]:
        """Extract podcast ID from Apple Podcasts URL."""
        # Match patterns like: id123456789
        match = re.search(r'id(\d+)', apple_url)
        return match.group(1) if match else None
    
    def get_rss_from_apple_id(self, podcast_id: str) -> Optional[str]:
        """Get RSS feed URL from Apple Podcasts using iTunes API."""
        try:
            params = {
                'id': podcast_id,
                'entity': 'podcast',
                'media': 'podcast'
            }
            
            response = self.session.get(self.apple_itunes_api, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('resultCount', 0) > 0:
                result = data['results'][0]
                rss_url = result.get('feedUrl')
                
                if rss_url:
                    print(f"✓ Found RSS feed: {rss_url}")
                    return rss_url
                else:
                    print("✗ No RSS feed found for this podcast")
            else:
                print("✗ Podcast not found in iTunes database")
                
        except Exception as e:
            print(f"✗ Error accessing iTunes API: {e}")
            
        return None
    
    def handle_apple_podcast_url(self, url: str, max_episodes: int = 1) -> bool:
        """Handle Apple Podcasts URL by converting to RSS feed."""
        print("Detected Apple Podcasts URL")
        
        podcast_id = self.extract_podcast_id(url)
        if not podcast_id:
            print("✗ Could not extract podcast ID from URL")
            print("URL should contain 'id' followed by numbers, e.g., id123456789")
            return False
        
        print(f"Podcast ID: {podcast_id}")
        
        rss_url = self.get_rss_from_apple_id(podcast_id)
        if not rss_url:
            return False
        
        # Now download from RSS feed
        return self.download_from_rss(rss_url, max_episodes)
    
    def download_from_rss(self, url: str, max_episodes: int = 1) -> bool:
        """Download episodes from RSS feed."""
        episodes = self.parse_rss_feed(url)
        
        if not episodes:
            print("✗ No audio episodes found in RSS feed.")
            return False
        
        print(f"Found {len(episodes)} episode(s)")
        
        success_count = 0
        # Download episodes (limited by max_episodes)
        for i, episode in enumerate(episodes[:max_episodes]):
            print(f"\n[{i+1}/{min(max_episodes, len(episodes))}]")
            if self.download_audio_file(episode['url'], episode['filename'], ask_filename=False):
                success_count += 1
            
            # Add delay between downloads to be respectful
            if i < len(episodes[:max_episodes]) - 1:
                time.sleep(1)
        
        print(f"\n✓ Successfully downloaded {success_count}/{min(max_episodes, len(episodes))} episodes")
        return success_count > 0
    
    def download_youtube_audio(self, url: str) -> bool:
        """Download audio from YouTube video with automatic browser cookie support."""
        if not YTDLP_AVAILABLE:
            print("❌ yt-dlp not installed. Cannot download from YouTube.")
            print("Install with: pip install yt-dlp")
            return False
        
        # List of browsers to try for cookie extraction (in order of preference)
        browsers_to_try = ['chrome', 'firefox', 'safari', 'edge', 'opera']
        
        for attempt, browser in enumerate(browsers_to_try):
            try:
                print(f"🎬 Processing YouTube URL... (attempt {attempt + 1}/{len(browsers_to_try)})")
                if attempt > 0:
                    print(f"🍪 Trying {browser.title()} browser cookies...")
                elif attempt == 0:
                    print(f"🍪 Using {browser.title()} browser cookies...")
                
                # Configure yt-dlp options with automatic cookie extraction
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'cookiesfrombrowser': (browser, None, None, None),  # (browser, profile, keyring, container)
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Get video info first
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown')
                    duration = info.get('duration', 0)
                    
                    print(f"📹 Title: {title}")
                    if duration:
                        mins, secs = divmod(duration, 60)
                        print(f"⏱️  Duration: {mins}m {secs}s")
                    
                    # Download the audio
                    print("⬇️  Downloading audio...")
                    ydl.download([url])
                    
                    print(f"✅ Successfully downloaded: {title}")
                    print(f"🍪 Success using {browser.title()} cookies!")
                    return True
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for specific error types
                if "sign in" in error_msg or "not a bot" in error_msg or "cookies" in error_msg:
                    print(f"🔐 Authentication required with {browser.title()}")
                    if attempt < len(browsers_to_try) - 1:
                        print(f"🔄 Trying next browser...")
                        continue
                elif "private" in error_msg or "unavailable" in error_msg:
                    print(f"❌ Video is private or unavailable: {e}")
                    return False
                elif "copyright" in error_msg:
                    print(f"❌ Copyright restriction: {e}")
                    return False
                elif "region" in error_msg or "country" in error_msg:
                    print(f"❌ Geographic restriction: {e}")
                    return False
                elif "no such browser" in error_msg or "browser not found" in error_msg:
                    print(f"⚠️  {browser.title()} browser not found, trying next...")
                    if attempt < len(browsers_to_try) - 1:
                        continue
                else:
                    print(f"⚠️  Error with {browser.title()}: {e}")
                    if attempt < len(browsers_to_try) - 1:
                        continue
                
                # If this is the last attempt, show final error
                if attempt == len(browsers_to_try) - 1:
                    print(f"❌ All browser cookie attempts failed. Final error: {e}")
                    print("💡 Suggestions:")
                    print("   1. Make sure you're logged into YouTube in your browser")
                    print("   2. Try visiting the video in your browser first")
                    print("   3. Check that the video is public and not region-locked")
                    print("   4. Try a different video URL")
                    return False
        
        return False
    
    def get_url_with_validation(self) -> str:
        """Prompt user for URL with validation and retry."""
        while True:
            url = input("请输入下载链接: ").strip()
            
            if not url:
                print("✗ 链接不能为空，请重新输入")
                continue
            
            print("🔍 验证链接中...")
            if self.is_valid_url(url):
                return url
            else:
                print("✗ 链接无效或无法访问，请检查后重新输入")
                print("💡 确保链接格式正确且网络连接正常")

    def download_from_url(self, url: str, max_episodes: int = 1) -> None:
        """Download podcast(s) from URL."""
        print(f"Processing URL: {url}")
        
        if self.is_audio_url(url):
            # Direct audio file
            self.download_audio_file(url)
        elif self.is_apple_podcast_url(url):
            # Apple Podcasts URL
            success = self.handle_apple_podcast_url(url, max_episodes)
            if not success:
                print("\n💡 Tip: Make sure the Apple Podcasts URL contains a podcast ID (e.g., id123456789)")
                print("💡 Some podcasts may have restricted access or require subscription.")
        elif self.is_youtube_url(url):
            # YouTube URL
            success = self.download_youtube_audio(url)
            if not success:
                print("\n💡 Tip: Make sure the YouTube video is public and not restricted.")
                print("💡 Some videos may have copyright or geographic restrictions.")
        else:
            # Try to parse as RSS feed
            self.download_from_rss(url, max_episodes)


def main():
    parser = argparse.ArgumentParser(
        description='Download podcast audio files',
        epilog='Supports RSS feeds, direct audio URLs, Apple Podcasts URLs, and YouTube videos.\n'
               'Note: Some content may require subscription or have access restrictions.'
    )
    parser.add_argument('url', nargs='?', help='Podcast URL (RSS feed, Apple Podcasts, or direct audio file)')
    parser.add_argument('-o', '--output', default='downloads', 
                       help='Output directory (default: downloads)')
    parser.add_argument('-n', '--max-episodes', type=int, default=1,
                       help='Maximum number of episodes to download (default: 1)')
    parser.add_argument('--cookies', type=str,
                       help='Path to cookies file for authentication (Netscape format)')
    parser.add_argument('--headers', type=str,
                       help='Additional headers as JSON string')
    
    args = parser.parse_args()
    
    downloader = PodcastDownloader(args.output)
    
    # Load cookies if provided
    if args.cookies and os.path.exists(args.cookies):
        try:
            from http.cookiejar import MozillaCookieJar
            cookie_jar = MozillaCookieJar(args.cookies)
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            downloader.session.cookies = cookie_jar
            print(f"✓ Loaded cookies from {args.cookies}")
        except Exception as e:
            print(f"⚠️ Could not load cookies: {e}")
    
    # Add custom headers if provided
    if args.headers:
        try:
            custom_headers = json.loads(args.headers)
            downloader.session.headers.update(custom_headers)
            print(f"✓ Added custom headers")
        except Exception as e:
            print(f"⚠️ Could not parse headers: {e}")
    
    # Get URL from argument or prompt user
    if args.url:
        url = args.url
    else:
        print("🎧 Podcast Audio Downloader")
        print("支持下载 RSS 订阅源、直接音频链接、Apple Podcasts 和 YouTube 视频")
        print()
        url = downloader.get_url_with_validation()
    
    downloader.download_from_url(url, args.max_episodes)


if __name__ == "__main__":
    main()