#!/usr/bin/env python3
"""
Test script for vocabulary database functionality
"""

from vocabulary_database import VocabularyDatabase

def test_vocabulary_database():
    print("🧪 测试词汇数据库功能...")
    
    # 初始化数据库
    db = VocabularyDatabase()
    
    # 测试词汇
    test_words = [
        "headquarters",
        "francisco", 
        "outrageous",
        "artificial",
        "intelligence",
        "sophisticated", 
        "comprehensive",
        "phenomenon",
        "anthropic",
        "the",
        "computer",
        "business"
    ]
    
    print(f"\n📝 测试 {len(test_words)} 个词汇:")
    
    # 测试不同用户水平
    user_levels = ['4.0', '5.0', '6.0', '7.0']
    
    for level in user_levels:
        print(f"\n👤 用户水平: {level}")
        print("=" * 50)
        
        difficult_count = 0
        for word in test_words:
            result = db.get_word_difficulty(word, level)
            if result:
                status = "🔴 困难" if result['is_difficult'] else "🟢 简单"
                print(f"{status} {word:15} - {result['cefr_level'] or 'N/A':2} | {result['definition'] or 'N/A'}")
                if result['is_difficult']:
                    difficult_count += 1
            else:
                print(f"❓ {word:15} - 数据库中未找到")
        
        print(f"📊 困难词汇数: {difficult_count}/{len(test_words)}")
    
    # 统计信息
    stats = db.get_stats()
    print(f"\n📈 数据库统计信息:")
    print(f"总词汇数: {stats['total_words']}")
    print(f"CEFR分布: {stats['cefr_distribution']}")
    print(f"学术词汇: {stats['academic_words']}")
    
    db.close()
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    test_vocabulary_database()