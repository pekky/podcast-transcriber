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

    def download_audio_file(self, url: str, filename: Optional[str] = None) -> bool:
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
                parsed_url = urllib.parse.urlparse(url)
                filename = os.path.basename(parsed_url.path) or "podcast_audio.mp3"
            
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
            if self.download_audio_file(episode['url'], episode['filename']):
                success_count += 1
            
            # Add delay between downloads to be respectful
            if i < len(episodes[:max_episodes]) - 1:
                time.sleep(1)
        
        print(f"\n✓ Successfully downloaded {success_count}/{min(max_episodes, len(episodes))} episodes")
        return success_count > 0
    
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
        else:
            # Try to parse as RSS feed
            self.download_from_rss(url, max_episodes)


def main():
    parser = argparse.ArgumentParser(
        description='Download podcast audio files',
        epilog='Supports RSS feeds, direct audio URLs, and Apple Podcasts URLs.\n'
               'Note: Some Apple Podcasts content may require subscription or have access restrictions.'
    )
    parser.add_argument('url', help='Podcast URL (RSS feed, Apple Podcasts, or direct audio file)')
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
    
    downloader.download_from_url(args.url, args.max_episodes)


if __name__ == "__main__":
    main()