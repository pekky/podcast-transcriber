#!/usr/bin/env python3
"""
Vocabulary Difficulty Assessment Service

This module provides API endpoints to assess vocabulary difficulty
based on multiple criteria including frequency, CEFR levels, and contextual usage.
"""

import os
import json
import requests
from typing import List, Dict, Optional
from flask import Blueprint, request, jsonify
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
import re

# 下载必要的NLTK数据
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

vocab_bp = Blueprint('vocabulary', __name__)

class VocabularyAnalyzer:
    def __init__(self):
        # 尝试使用专业词汇数据库
        try:
            from vocabulary_database import VocabularyDatabase
            self.vocab_db = VocabularyDatabase()
            self.use_database = True
            print("✅ 使用专业词汇数据库")
        except ImportError:
            self.vocab_db = None
            self.use_database = False
            print("⚠️ 使用备用词汇分析")
            # 备用数据
            self.word_frequency = self._load_word_frequency()
            self.cefr_levels = self._load_cefr_levels()
            self.academic_words = self._load_academic_words()
        
    def _load_word_frequency(self) -> Dict[str, int]:
        """加载词频数据（基于Google 10000最常见英语单词）"""
        # 这里可以加载真实的词频数据文件
        # 简化示例：返回一些基本的词频数据
        common_words = {
            'the': 1, 'and': 2, 'of': 3, 'to': 4, 'a': 5, 'in': 6, 'for': 7, 'is': 8, 
            'on': 9, 'that': 10, 'by': 11, 'this': 12, 'with': 13, 'i': 14, 'you': 15,
            'it': 16, 'not': 17, 'or': 18, 'be': 19, 'are': 20, 'from': 21, 'at': 22,
            'as': 23, 'your': 24, 'all': 25, 'have': 26, 'new': 27, 'more': 28, 'an': 29,
            'was': 30, 'we': 31, 'will': 32, 'home': 33, 'can': 34, 'us': 35, 'about': 36,
            'if': 37, 'page': 38, 'my': 39, 'has': 40, 'search': 41, 'free': 42, 'but': 43,
            'our': 44, 'one': 45, 'other': 46, 'do': 47, 'no': 48, 'information': 49, 'time': 50
        }
        
        # 扩展更多高频词
        medium_freq_words = {
            'technology': 1500, 'computer': 1800, 'system': 2000, 'business': 2200,
            'development': 2500, 'management': 2800, 'important': 3000, 'different': 3200,
            'following': 3500, 'without': 3800, 'program': 4000, 'problem': 4200,
            'complete': 4500, 'room': 4800, 'until': 5000
        }
        
        low_freq_words = {
            'sophisticated': 8000, 'phenomenon': 8500, 'comprehensive': 7500, 
            'artificial': 6000, 'intelligence': 5500, 'algorithm': 9000,
            'sustainability': 9500, 'unprecedented': 9800, 'anthropic': 9900,
            'outrageous': 8800, 'diagnostic': 8200, 'therapeutic': 9200
        }
        
        return {**common_words, **medium_freq_words, **low_freq_words}
    
    def _load_cefr_levels(self) -> Dict[str, str]:
        """加载CEFR (欧洲语言共同参考框架) 词汇分级数据"""
        return {
            # A1 Level (Beginner)
            'hello': 'A1', 'yes': 'A1', 'no': 'A1', 'please': 'A1', 'thank': 'A1',
            'good': 'A1', 'bad': 'A1', 'big': 'A1', 'small': 'A1', 'new': 'A1',
            
            # A2 Level (Elementary) 
            'important': 'A2', 'different': 'A2', 'possible': 'A2', 'necessary': 'A2',
            'available': 'A2', 'interesting': 'A2', 'difficult': 'A2',
            
            # B1 Level (Intermediate)
            'technology': 'B1', 'computer': 'B1', 'business': 'B1', 'development': 'B1',
            'management': 'B1', 'system': 'B1', 'program': 'B1', 'process': 'B1',
            
            # B2 Level (Upper-Intermediate) 
            'comprehensive': 'B2', 'artificial': 'B2', 'intelligence': 'B2',
            'innovative': 'B2', 'sustainable': 'B2', 'fundamental': 'B2',
            
            # C1 Level (Advanced)
            'sophisticated': 'C1', 'unprecedented': 'C1', 'phenomenon': 'C1',
            'theoretical': 'C1', 'methodology': 'C1', 'implementation': 'C1',
            
            # C2 Level (Proficiency)
            'anthropic': 'C2', 'epistemological': 'C2', 'paradigmatic': 'C2',
            'quintessential': 'C2', 'ubiquitous': 'C2'
        }
    
    def _load_academic_words(self) -> set:
        """加载学术词汇列表 (Academic Word List)"""
        return {
            'analysis', 'approach', 'area', 'assessment', 'assume', 'authority',
            'available', 'benefit', 'concept', 'consistent', 'constitutional', 'context',
            'contract', 'create', 'data', 'definition', 'derived', 'distribution',
            'economic', 'environment', 'established', 'estimate', 'evidence',
            'export', 'factors', 'financial', 'formula', 'function', 'identified',
            'income', 'indicate', 'individual', 'interpretation', 'involved',
            'issues', 'labor', 'legal', 'legislation', 'major', 'method',
            'occur', 'percent', 'period', 'policy', 'principle', 'procedure',
            'process', 'required', 'research', 'response', 'role', 'section',
            'significant', 'similar', 'source', 'specific', 'structure', 'theory',
            'variables', 'comprehensive', 'sophisticated', 'phenomenon', 'unprecedented'
        }
    
    def assess_word_difficulty(self, word: str, user_level: str) -> Dict[str, any]:
        """
        评估单词难度
        
        Args:
            word: 要评估的单词
            user_level: 用户英语水平 ('4.0', '5.0', '6.0', '7.0')
            
        Returns:
            Dict containing difficulty assessment
        """
        word_lower = word.lower().strip()
        
        # 过滤太短的词或非字母词
        if len(word_lower) < 3 or not word_lower.isalpha():
            return {'word': word, 'is_difficult': False, 'reason': 'too_short_or_invalid'}
        
        # 优先使用专业数据库
        if self.use_database and self.vocab_db:
            try:
                db_result = self.vocab_db.get_word_difficulty(word_lower, user_level)
                if db_result:
                    return db_result
            except Exception as e:
                print(f"数据库查询失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 备用分析逻辑（与之前相同）
        assessment = {
            'word': word,
            'is_difficult': False,
            'difficulty_level': None,
            'cefr_level': None,
            'frequency_rank': None,
            'is_academic': False,
            'definition': None,
            'phonetic': None,
            'reasons': []
        }
        
        # 1. 检查词频
        if hasattr(self, 'word_frequency'):
            freq_rank = self.word_frequency.get(word_lower)
            if freq_rank:
                assessment['frequency_rank'] = freq_rank
            
        # 2. 检查CEFR分级
        if hasattr(self, 'cefr_levels'):
            cefr_level = self.cefr_levels.get(word_lower)
            if cefr_level:
                assessment['cefr_level'] = cefr_level
            
        # 3. 检查是否为学术词汇
        if hasattr(self, 'academic_words') and word_lower in self.academic_words:
            assessment['is_academic'] = True
            assessment['reasons'].append('academic_word')
            
        # 4. 基于用户水平判断是否困难
        user_level_mapping = {
            '4.0': {'max_freq': 1000, 'max_cefr': 'A2'},
            '5.0': {'max_freq': 2000, 'max_cefr': 'B1'},
            '6.0': {'max_freq': 4000, 'max_cefr': 'B2'},
            '7.0': {'max_freq': 6000, 'max_cefr': 'C1'}
        }
        
        user_limits = user_level_mapping.get(user_level, user_level_mapping['6.0'])
        
        # 词频判断
        freq_rank = assessment.get('frequency_rank')
        cefr_level = assessment.get('cefr_level')
        
        if freq_rank and freq_rank > user_limits['max_freq']:
            assessment['is_difficult'] = True
            assessment['reasons'].append(f'low_frequency_{freq_rank}')
            
        # CEFR级别判断
        if cefr_level:
            cefr_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
            if cefr_level in cefr_order and user_limits['max_cefr'] in cefr_order:
                if cefr_order.index(cefr_level) > cefr_order.index(user_limits['max_cefr']):
                    assessment['is_difficult'] = True
                    assessment['reasons'].append(f'high_cefr_{cefr_level}')
                    
        # 5. 基于长度的备用判断
        if not assessment['is_difficult'] and len(word_lower) > 8:
            # 对于没有在数据库中的长单词，进行基本判断
            if not freq_rank and not cefr_level:
                assessment['is_difficult'] = True
                assessment['reasons'].append('unknown_long_word')
                
        # 6. 设置难度级别
        if assessment['is_difficult']:
            if cefr_level in ['C2']:
                assessment['difficulty_level'] = 'high'
            elif cefr_level in ['C1'] or (freq_rank and freq_rank > 8000):
                assessment['difficulty_level'] = 'advanced'
            else:
                assessment['difficulty_level'] = 'medium'
        
        # 7. 尝试获取定义和音标
        try:
            synsets = wordnet.synsets(word_lower)
            if synsets:
                assessment['definition'] = synsets[0].definition()
                # 简化的音标生成
                assessment['phonetic'] = f"/ˈ{word_lower}/"
        except:
            pass
            
        return assessment
    
    def analyze_vocabulary_batch(self, words: List[str], user_level: str) -> List[Dict]:
        """批量分析词汇"""
        results = []
        for word in words:
            assessment = self.assess_word_difficulty(word, user_level)
            if assessment['is_difficult']:
                results.append(assessment)
        return results
    
    def analyze_sentence_complexity(self, sentence: str, user_level: str) -> Dict:
        """分析句子复杂度"""
        sentence = sentence.strip()
        
        complexity_assessment = {
            'sentence': sentence,
            'is_complex': False,
            'complexity_level': 'Simple',
            'reasons': [],
            'word_count': 0,
            'difficult_words': []
        }
        
        # 词汇化 (使用简单分割)
        words = re.findall(r'\b[a-zA-Z]+\b', sentence.lower())
        words = [word for word in words if word.isalpha()]
        complexity_assessment['word_count'] = len(words)
        
        # 检查困难词汇
        difficult_words = []
        for word in set(words):  # 去重
            assessment = self.assess_word_difficulty(word, user_level)
            if assessment['is_difficult']:
                difficult_words.append(word)
                
        complexity_assessment['difficult_words'] = difficult_words
        
        # 复杂度指标
        high_complexity_markers = [
            'therefore', 'however', 'nevertheless', 'consequently', 
            'furthermore', 'moreover', 'whereas', 'notwithstanding'
        ]
        
        medium_complexity_markers = [
            'although', 'because', 'since', 'unless', 'whether', 
            'while', 'despite', 'regarding', 'concerning'
        ]
        
        # 检查复杂度标记
        for marker in high_complexity_markers:
            if marker in words:
                complexity_assessment['is_complex'] = True
                complexity_assessment['complexity_level'] = 'Highly Complex'
                complexity_assessment['reasons'].append(f'high_complexity_marker_{marker}')
                break
                
        if not complexity_assessment['is_complex']:
            for marker in medium_complexity_markers:
                if marker in words:
                    complexity_assessment['is_complex'] = True
                    complexity_assessment['complexity_level'] = 'Complex'
                    complexity_assessment['reasons'].append(f'medium_complexity_marker_{marker}')
                    break
        
        # 基于长度和标点的复杂度判断
        comma_count = sentence.count(',')
        word_count = len(words)
        
        if word_count > 25 and comma_count > 2:
            complexity_assessment['is_complex'] = True
            complexity_assessment['complexity_level'] = 'Highly Complex'
            complexity_assessment['reasons'].append('long_multi_clause')
        elif word_count > 20 and comma_count > 1:
            if not complexity_assessment['is_complex']:
                complexity_assessment['is_complex'] = True
                complexity_assessment['complexity_level'] = 'Complex'
                complexity_assessment['reasons'].append('moderately_long_with_clauses')
        
        # 困难词汇密度
        if len(difficult_words) > 3:
            complexity_assessment['is_complex'] = True
            complexity_assessment['reasons'].append('high_difficult_word_density')
            
        return complexity_assessment

# 创建全局分析器实例
vocab_analyzer = VocabularyAnalyzer()

@vocab_bp.route('/api/analyze-vocabulary', methods=['POST'])
def analyze_vocabulary():
    """词汇分析API端点"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
            
        text = data.get('text', '')
        user_level = data.get('user_level', '6.0')
        
        print(f"📝 接收到词汇分析请求: text长度={len(text)}, user_level={user_level}")
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        # 提取单词 (使用简单分割避免NLTK问题)
        import re
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        words = [word for word in words if word.isalpha() and len(word) > 3]
        unique_words = list(set(words))
        
        print(f"🔍 提取到 {len(unique_words)} 个独特单词")
        
        # 分析词汇
        difficult_words = vocab_analyzer.analyze_vocabulary_batch(unique_words, user_level)
        
        print(f"📊 找到 {len(difficult_words)} 个困难词汇")
        
        # 分析句子
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        complex_sentences = []
        for sentence in sentences:
            assessment = vocab_analyzer.analyze_sentence_complexity(sentence, user_level)
            if assessment['is_complex']:
                complex_sentences.append(assessment)
        
        print(f"📝 找到 {len(complex_sentences)} 个复杂句子")
        
        result = {
            'success': True,
            'vocabulary': {
                'total_words': len(unique_words),
                'difficult_words': difficult_words[:8],  # 限制返回数量
                'difficulty_count': len(difficult_words)
            },
            'sentences': {
                'total_sentences': len(sentences),
                'complex_sentences': complex_sentences[:5],  # 限制返回数量
                'complexity_count': len(complex_sentences)
            },
            'user_level': user_level
        }
        
        print("✅ 词汇分析完成，返回结果")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ 词汇分析API错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vocab_bp.route('/api/word-difficulty', methods=['POST'])
def check_word_difficulty():
    """单词难度检查API"""
    try:
        data = request.get_json()
        word = data.get('word', '')
        user_level = data.get('user_level', '6.0')
        
        if not word:
            return jsonify({
                'success': False,
                'error': 'No word provided'
            }), 400
        
        assessment = vocab_analyzer.assess_word_difficulty(word, user_level)
        
        return jsonify({
            'success': True,
            'assessment': assessment
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500