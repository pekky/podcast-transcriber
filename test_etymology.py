#!/usr/bin/env python3
"""
测试词源信息提取功能
"""

from vocabulary_analyzer import VocabularyAnalyzer
import json

def test_etymology():
    analyzer = VocabularyAnalyzer()
    
    # 测试几个词汇的词源信息
    test_words = ['government', 'engineering', 'technology']
    
    for word in test_words:
        print(f"\n{'='*50}")
        print(f"测试词汇: {word}")
        print(f"{'='*50}")
        
        # 获取在线词源信息
        etymology_info = analyzer.fetch_etymology_from_etymonline(word)
        
        if etymology_info['etymology_history']:
            print(f"✅ 词源历史: {etymology_info['etymology_history'][:100]}...")
            print(f"✅ 语言起源: {etymology_info['language_origin']}")
            print(f"✅ 词根含义: {etymology_info['root_meaning']}")
            print(f"✅ 相关词汇: {', '.join(etymology_info['related_words'])}")
            
            if etymology_info['evolution_path']:
                print("✅ 演变路径:")
                for evolution in etymology_info['evolution_path']:
                    print(f"   - {evolution['period']}: {evolution['form']}")
        else:
            print("❌ 未获取到词源信息")

if __name__ == "__main__":
    test_etymology()