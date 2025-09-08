#!/usr/bin/env python3
"""
调试词源网站结构
"""

import requests
from bs4 import BeautifulSoup
import urllib.parse

def debug_etymonline(word):
    try:
        encoded_word = urllib.parse.quote(word.lower())
        url = f"https://www.etymonline.com/word/{encoded_word}"
        print(f"访问URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"响应状态: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 保存HTML到文件查看结构
        with open(f'debug_{word}.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"HTML已保存到 debug_{word}.html")
        
        # 查找所有包含词源信息的可能元素
        print(f"\n所有文本内容前500字符:")
        print(soup.get_text()[:500])
        
        # 查找主要内容区域
        content_areas = soup.find_all(['div', 'section', 'p'], class_=True)
        print(f"\n找到 {len(content_areas)} 个带class的内容区域")
        
        for i, area in enumerate(content_areas[:10]):
            if area.get_text().strip():
                print(f"\n区域 {i}: class='{area.get('class')}'")
                text = area.get_text().strip()
                print(f"内容: {text[:100]}...")
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    debug_etymonline("government")