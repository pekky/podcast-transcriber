#!/usr/bin/env python3
"""
Cookie Extraction Helper

This script helps extract cookies from your browser for use with the podcast downloader.
Useful when downloading podcasts that require authentication.
"""

import json
import sqlite3
import os
import shutil
from pathlib import Path
import argparse


def extract_chrome_cookies(domain: str = "podcasts.apple.com") -> str:
    """Extract cookies from Chrome for a specific domain."""
    # Chrome cookie database paths
    chrome_paths = [
        "~/Library/Application Support/Google/Chrome/Default/Cookies",  # macOS
        "~/.config/google-chrome/Default/Cookies",  # Linux
        "~/AppData/Local/Google/Chrome/User Data/Default/Cookies"  # Windows
    ]
    
    for path in chrome_paths:
        cookie_path = Path(path).expanduser()
        if cookie_path.exists():
            try:
                # Make a copy of the database (Chrome locks it)
                temp_path = cookie_path.parent / "Cookies_temp"
                shutil.copy2(cookie_path, temp_path)
                
                conn = sqlite3.connect(str(temp_path))
                cursor = conn.cursor()
                
                # Query cookies for the domain
                cursor.execute("""
                    SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                    FROM cookies
                    WHERE host_key LIKE ?
                """, (f'%{domain}%',))
                
                cookies = cursor.fetchall()
                conn.close()
                
                # Clean up temp file
                os.remove(temp_path)
                
                if cookies:
                    # Convert to Netscape format
                    netscape_content = "# Netscape HTTP Cookie File\n"
                    for cookie in cookies:
                        name, value, host_key, path, expires_utc, is_secure, is_httponly = cookie
                        secure = "TRUE" if is_secure else "FALSE"
                        netscape_content += f"{host_key}\tTRUE\t{path}\t{secure}\t{expires_utc}\t{name}\t{value}\n"
                    
                    return netscape_content
                    
            except Exception as e:
                print(f"Error reading Chrome cookies: {e}")
                continue
    
    return ""


def extract_safari_cookies(domain: str = "podcasts.apple.com") -> str:
    """Extract cookies from Safari for a specific domain."""
    safari_path = Path("~/Library/Cookies/Cookies.binarycookies").expanduser()
    
    if safari_path.exists():
        print("Safari cookies found, but binary format requires special parsing.")
        print("Consider using browser extensions to export cookies instead.")
    
    return ""


def save_cookies_file(content: str, filename: str = "cookies.txt") -> None:
    """Save cookies to a file."""
    if content:
        with open(filename, 'w') as f:
            f.write(content)
        print(f"✓ Cookies saved to {filename}")
    else:
        print("✗ No cookies found")


def main():
    parser = argparse.ArgumentParser(description='Extract browser cookies for podcast downloading')
    parser.add_argument('-d', '--domain', default='podcasts.apple.com',
                       help='Domain to extract cookies for (default: podcasts.apple.com)')
    parser.add_argument('-o', '--output', default='cookies.txt',
                       help='Output file for cookies (default: cookies.txt)')
    parser.add_argument('-b', '--browser', choices=['chrome', 'safari'], default='chrome',
                       help='Browser to extract from (default: chrome)')
    
    args = parser.parse_args()
    
    print(f"Extracting cookies for {args.domain} from {args.browser}")
    
    if args.browser == 'chrome':
        cookies = extract_chrome_cookies(args.domain)
    else:
        cookies = extract_safari_cookies(args.domain)
    
    save_cookies_file(cookies, args.output)
    
    if cookies:
        print(f"\nUsage:")
        print(f"python podcast_downloader.py --cookies {args.output} <podcast_url>")
    else:
        print("\n💡 Alternative: Use browser extensions like 'cookies.txt' to export cookies manually")


if __name__ == "__main__":
    main()