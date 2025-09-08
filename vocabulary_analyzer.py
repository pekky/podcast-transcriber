#!/usr/bin/env python3
"""
Vocabulary Analysis Tool for English Learners
从音频转录文件中提取和分析适合特定英语水平的词汇

This tool analyzes transcription files and generates vocabulary study guides
with detailed explanations, pronunciations, and examples.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import argparse
from collections import Counter
import nltk
from nltk.corpus import wordnet, cmudict
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
from nltk.parse.stanford import StanfordDependencyParser
import requests
import time
import statistics
from cefr_vocabulary import CEFRVocabulary
from bs4 import BeautifulSoup
import urllib.parse

# Download required NLTK data
def ensure_nltk_data():
    required_data = [
        'punkt', 'punkt_tab', 'averaged_perceptron_tagger', 
        'averaged_perceptron_tagger_eng', 'wordnet', 'cmudict', 'stopwords'
    ]
    
    print("📥 Checking and downloading required NLTK data...")
    for name in required_data:
        try:
            nltk.download(name, quiet=True)
        except Exception as e:
            print(f"   Warning: Could not download {name}: {e}")

ensure_nltk_data()


class VocabularyAnalyzer:
    def __init__(self, target_level: str = "B1+"):
        """
        初始化词汇分析器
        
        Args:
            target_level: 目标英语水平 (CEFR标准: A1, A2, B1, B1+, B2, C1, C2)
        """
        self.target_level = target_level
        self.pronunciation_dict = cmudict.dict()
        self.stop_words = set(stopwords.words('english'))
        
        # 初始化CEFR词汇数据库
        self.cefr_vocab = CEFRVocabulary()
        
        # 根据目标水平确定基础词汇（需要过滤的）
        if target_level in ['A1', 'A2']:
            self.basic_words = set()  # 对于初学者，不过滤词汇
        elif target_level in ['B1', 'B1+']:
            self.basic_words = self.cefr_vocab.get_words_by_level('A1')
        elif target_level == 'B2':
            self.basic_words = self.cefr_vocab.get_words_by_level('A1').union(
                self.cefr_vocab.get_words_by_level('A2')
            )
        else:  # C1, C2
            self.basic_words = self.cefr_vocab.get_all_basic_words().union(
                self.cefr_vocab.get_words_by_level('B1')
            )
        
        # 存储原文文本用于例句提取
        self.source_text = ""
        
        # 词汇难度级别定义
        self.difficulty_levels = {
            'basic': {'min_length': 3, 'max_length': 6, 'common_prefixes': [], 'common_suffixes': []},
            'intermediate': {'min_length': 5, 'max_length': 10, 'common_prefixes': ['un-', 're-', 'pre-'], 'common_suffixes': ['-tion', '-ly', '-ing']},
            'advanced': {'min_length': 7, 'max_length': 15, 'common_prefixes': ['inter-', 'trans-', 'auto-'], 'common_suffixes': ['-ment', '-ism', '-ary']},
            'expert': {'min_length': 8, 'max_length': 20, 'common_prefixes': ['anti-', 'counter-', 'pseudo-'], 'common_suffixes': ['-ology', '-cracy', '-phobia']}
        }
        
        # 词汇库 - 按难度分级的高频词汇
        self.vocabulary_database = self._load_vocabulary_database()
    
    def _load_vocabulary_database(self) -> Dict:
        """加载词汇数据库（包含词根、词缀、释义等）"""
        # 这里可以扩展为从外部文件加载更完整的词汇数据库
        return {
            # 词根词缀数据库
            'roots': {
                'vers': {'meaning': 'turn', 'examples': ['reverse', 'universe', 'adverse']},
                'struct': {'meaning': 'build', 'examples': ['structure', 'construct', 'destructive']},
                'crat': {'meaning': 'rule', 'examples': ['democrat', 'autocrat', 'bureaucrat']},
                'auto': {'meaning': 'self', 'examples': ['automatic', 'autonomous', 'autobiography']},
                'techno': {'meaning': 'technology', 'examples': ['technology', 'technique', 'technical']},
                'hydro': {'meaning': 'water', 'examples': ['hydrogen', 'hydraulic', 'hydrate']},
            },
            'prefixes': {
                'anti-': 'against, opposite',
                'auto-': 'self',
                'inter-': 'between, among',
                'trans-': 'across, through',
                'counter-': 'against, opposite',
                'over-': 'too much, above',
                'under-': 'too little, below',
                'semi-': 'half, partially'
            },
            'suffixes': {
                '-ism': 'doctrine, belief system',
                '-cracy': 'rule, government',
                '-ology': 'study of',
                '-tion': 'action, process',
                '-ment': 'result, action',
                '-ary': 'relating to',
                '-ive': 'tending to',
                '-ous': 'having the quality of'
            }
        }
    
    def extract_text_from_transcript(self, file_path: Path) -> str:
        """从转录文件中提取纯文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除说话人标识和空行
            lines = content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    # 移除说话人标识
                    line = re.sub(r'^[A-Z]:\s*', '', line)
                    line = re.sub(r'^Speaker:\s*', '', line)
                    line = re.sub(r'^Unknown:\s*', '', line)
                    
                    # 移除行号（如果存在）
                    line = re.sub(r'^\d+→', '', line)
                    
                    if line.strip():
                        text_lines.append(line.strip())
            
            result_text = ' '.join(text_lines)
            print(f"🔍 提取的文本预览: {result_text[:200]}...")
            
            # 保存原文用于例句提取
            self.source_text = result_text
            
            return result_text
            
        except Exception as e:
            print(f"❌ Error reading file {file_path}: {e}")
            return ""
    
    def get_pronunciation(self, word: str) -> str:
        """获取单词的音标发音"""
        word_lower = word.lower()
        if word_lower in self.pronunciation_dict:
            # 转换CMU音标为IPA近似格式
            arpabet = self.pronunciation_dict[word_lower][0]
            ipa = self._arpabet_to_ipa(arpabet)
            return f"/{ipa}/"
        return "/pronunciation not found/"
    
    def _arpabet_to_ipa(self, arpabet: List[str]) -> str:
        """将CMU音标转换为IPA近似格式（简化版）"""
        # 这是一个简化的转换，实际应用中需要更完整的映射表
        mapping = {
            'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔ', 'AW': 'aʊ', 'AY': 'aɪ',
            'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'EH': 'e', 'ER': 'ər',
            'EY': 'eɪ', 'F': 'f', 'G': 'ɡ', 'HH': 'h', 'IH': 'ɪ', 'IY': 'i',
            'JH': 'dʒ', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ŋ',
            'OW': 'oʊ', 'OY': 'ɔɪ', 'P': 'p', 'R': 'r', 'S': 's', 'SH': 'ʃ',
            'T': 't', 'TH': 'θ', 'UH': 'ʊ', 'UW': 'u', 'V': 'v', 'W': 'w',
            'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'
        }
        
        result = []
        for phone in arpabet:
            # 移除重音标记
            clean_phone = re.sub(r'\d', '', phone)
            if clean_phone in mapping:
                result.append(mapping[clean_phone])
            else:
                result.append(clean_phone.lower())
        
        return ''.join(result)
    
    def analyze_word_difficulty(self, word: str) -> str:
        """基于CEFR标准分析单词难度级别"""
        word_lower = word.lower()
        
        # 使用CEFR数据库确定词汇级别
        cefr_level = self.cefr_vocab.get_level_for_word(word_lower)
        
        # 将CEFR级别映射到简化难度级别
        cefr_to_difficulty = {
            'A1': 'basic',
            'A2': 'basic', 
            'B1': 'intermediate',
            'B2': 'intermediate',
            'C1': 'advanced',
            'C2': 'expert'
        }
        
        return cefr_to_difficulty.get(cefr_level, 'expert')
    
    def _has_complex_morphology(self, word: str) -> bool:
        """检查单词是否有复杂的词汇形态（词根、词缀）"""
        complex_prefixes = ['inter-', 'trans-', 'counter-', 'pseudo-', 'auto-', 'anti-', 'semi-', 'multi-', 'super-', 'ultra-']
        complex_suffixes = ['-tion', '-ism', '-ology', '-cracy', '-ment', '-ness', '-ship', '-ward', '-wise', '-able', '-ible']
        
        word_lower = word.lower()
        
        for prefix in complex_prefixes:
            if word_lower.startswith(prefix.replace('-', '')):
                return True
        
        for suffix in complex_suffixes:
            if word_lower.endswith(suffix.replace('-', '')):
                return True
        
        return False
    
    def _is_common_word_pattern(self, word: str) -> bool:
        """检查是否为常见词汇模式（如简单的动名词、形容词等）"""
        word_lower = word.lower()
        
        # 常见的简单模式
        simple_patterns = [
            r'.*ing$',  # 简单进行时
            r'.*ed$',   # 简单过去式
            r'.*er$',   # 简单比较级
            r'.*ly$',   # 简单副词
            r'.*s$',    # 复数形式
        ]
        
        for pattern in simple_patterns:
            if re.match(pattern, word_lower):
                return True
        
        return False
    
    def _is_academic_or_technical_word(self, word: str) -> bool:
        """检查是否为学术或技术词汇"""
        word_lower = word.lower()
        
        # 学术/技术词汇的特征
        academic_patterns = [
            r'.*ology$',    # 学科名称
            r'.*graphy$',   # 学科/技术
            r'.*ography$',  # 学科
            r'.*ical$',     # 学术形容词
            r'.*istic$',    # 学术形容词
            r'.*ization$',  # 过程名词
            r'.*isation$',  # 过程名词(英式)
        ]
        
        # 学术/技术前缀
        academic_prefixes = ['bio', 'geo', 'eco', 'techno', 'socio', 'psycho', 'neuro', 'micro', 'macro']
        
        for pattern in academic_patterns:
            if re.match(pattern, word_lower):
                return True
        
        for prefix in academic_prefixes:
            if word_lower.startswith(prefix) and len(word) > len(prefix) + 2:
                return True
        
        return False
    
    def extract_sentences_from_source(self, word: str) -> List[str]:
        """从原文中提取包含指定词汇的句子"""
        if not self.source_text:
            return []
        
        sentences = sent_tokenize(self.source_text)
        word_sentences = []
        word_lower = word.lower()
        
        for sentence in sentences:
            # 检查句子是否包含目标词汇
            sentence_words = word_tokenize(sentence.lower())
            
            # 精确匹配词汇（包括词汇的变形）
            if any(word_lower in w or w in word_lower for w in sentence_words if len(w) > 3):
                cleaned_sentence = self._clean_sentence_for_example(sentence)
                
                # 过滤掉太长或太短的句子
                if 5 <= len(cleaned_sentence.split()) <= 30:
                    word_sentences.append(cleaned_sentence)
        
        # 返回最好的例句（按长度和复杂度排序）
        word_sentences.sort(key=lambda x: (len(x.split()), x.count(',')))
        return word_sentences[:3]
    
    def _clean_sentence_for_example(self, sentence: str) -> str:
        """清理句子用作例句"""
        # 移除说话人标识
        sentence = re.sub(r'^[A-Z]:\s*', '', sentence)
        sentence = re.sub(r'^Speaker:\s*', '', sentence)
        sentence = re.sub(r'^Unknown:\s*', '', sentence)
        
        # 移除多余的空格和标点
        sentence = re.sub(r'\s+', ' ', sentence)
        sentence = sentence.strip()
        
        # 确保句子以大写字母开头，适当的标点结尾
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
        
        return sentence
    
    def fetch_cambridge_dictionary_info(self, word: str) -> Dict:
        """从Cambridge Dictionary获取例句、音标和词汇信息"""
        try:
            # URL编码词汇
            encoded_word = urllib.parse.quote(word.lower())
            url = f"https://dictionary.cambridge.org/dictionary/english/{encoded_word}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 初始化返回结果
            result = {
                'examples': [],
                'pronunciation': '',
                'etymology': '',
                'part_of_speech': ''
            }
            
            # 获取例句
            example_selectors = [
                '.eg',  # 主要例句选择器
                '.examp',  # 备用选择器
                '.dexamp',  # 另一种格式
                '.examp .eg'  # 嵌套格式
            ]
            
            for selector in example_selectors:
                example_elements = soup.select(selector)
                for elem in example_elements:
                    example_text = elem.get_text().strip()
                    if example_text and len(example_text.split()) >= 5:
                        # 清理例句
                        example_text = re.sub(r'\s+', ' ', example_text)
                        result['examples'].append(example_text)
                
                if result['examples']:
                    break
            
            # 获取音标 - Cambridge使用多种音标选择器
            pronunciation_selectors = [
                '.ipa',  # IPA音标
                '.pron',  # 发音
                '.us .pron',  # 美式发音
                '.uk .pron',  # 英式发音
                'span[title="International Phonetic Alphabet"]'  # IPA标题
            ]
            
            for selector in pronunciation_selectors:
                pron_elem = soup.select_one(selector)
                if pron_elem:
                    pronunciation = pron_elem.get_text().strip()
                    if pronunciation:
                        result['pronunciation'] = f"/{pronunciation}/"
                        break
            
            # 获取词性
            pos_selectors = [
                '.pos',  # 词性
                '.part-of-speech',  # 词性
                '.posgram',  # 词性语法
            ]
            
            for selector in pos_selectors:
                pos_elem = soup.select_one(selector)
                if pos_elem:
                    result['part_of_speech'] = pos_elem.get_text().strip()
                    break
            
            # 限制例句数量
            result['examples'] = result['examples'][:3]
            
            return result
            
        except Exception as e:
            print(f"   Warning: Could not fetch dictionary info from Cambridge for '{word}': {e}")
            return {'examples': [], 'pronunciation': '', 'etymology': '', 'part_of_speech': ''}
    
    def fetch_etymology_from_etymonline(self, word: str) -> Dict:
        """从Etymology Online获取详细词源信息，包括演变历史和相关词汇"""
        try:
            # URL编码词汇
            encoded_word = urllib.parse.quote(word.lower())
            url = f"https://www.etymonline.com/word/{encoded_word}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result = {
                'etymology_history': '',
                'root_meaning': '',
                'related_words': [],
                'language_origin': '',
                'evolution_path': []
            }
            
            # 查找主要词源信息 - Etymology Online使用JSON数据
            full_etymology = ""
            
            # 从页面文本中提取词源信息
            page_text = soup.get_text()
            
            # 查找典型的词源模式
            etymology_patterns = [
                r'late \d+c\..*?from.*?from.*?[.!]',  # late 14c., ... from ... from ...
                r'mid-\d+c\..*?from.*?from.*?[.!]',   # mid-15c., ... from ... from ...
                r'early \d+c\..*?from.*?from.*?[.!]', # early 16c., ... from ... from ...
                r'from.*?from.*?from.*?[.!]',         # from ... from ... from ...
                r'\d+s,.*?from.*?[.!]',               # 1540s, ... from ...
            ]
            
            for pattern in etymology_patterns:
                match = re.search(pattern, page_text, re.DOTALL | re.IGNORECASE)
                if match:
                    full_etymology = match.group(0)
                    # 清理和截短
                    full_etymology = re.sub(r'\s+', ' ', full_etymology)
                    if len(full_etymology) > 200:
                        full_etymology = full_etymology[:200] + "..."
                    break
            
            # 如果没有找到模式，尝试直接查找关键短语
            if not full_etymology:
                text_parts = page_text.split()
                for i, part in enumerate(text_parts):
                    if 'etymology' in part.lower() or 'late' in part or 'from' in part:
                        # 提取周围的文本
                        start = max(0, i-5)
                        end = min(len(text_parts), i+20)
                        full_etymology = ' '.join(text_parts[start:end])
                        if len(full_etymology) > 50:
                            break
            
            if full_etymology:
                # 清理文本
                full_etymology = re.sub(r'\s+', ' ', full_etymology)
                result['etymology_history'] = full_etymology[:300] + "..." if len(full_etymology) > 300 else full_etymology
                
                # 提取语言起源
                language_patterns = [
                    r'from\s+(Old|Middle|Late|Proto-)?(\w+)\s+',
                    r'(Latin|Greek|French|German|Old English|Proto-Indo-European)\s+',
                    r'via\s+(\w+)\s+'
                ]
                for pattern in language_patterns:
                    match = re.search(pattern, full_etymology, re.IGNORECASE)
                    if match:
                        result['language_origin'] = match.group(0).strip()
                        break
                
                # 提取词根含义
                meaning_patterns = [
                    r'"([^"]+)"',  # 引号内的含义
                    r'meaning\s+"([^"]+)"',
                    r'literally\s+"([^"]+)"'
                ]
                for pattern in meaning_patterns:
                    match = re.search(pattern, full_etymology)
                    if match:
                        result['root_meaning'] = match.group(1)
                        break
            
            # 查找相关词汇
            related_selectors = [
                'a[href*="/word/"]',  # 链接到其他词汇的标签
                '.related-words a',
                '.word-family a'
            ]
            
            related_words = set()
            for selector in related_selectors:
                links = soup.select(selector)
                for link in links[:15]:  # 限制数量
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    if '/word/' in href and text and text.lower() != word.lower() and len(text) > 2:
                        # 过滤掉明显不相关的词汇
                        if any(char.isalpha() for char in text) and not text.isupper():
                            related_words.add(text.lower())
                        if len(related_words) >= 8:  # 限制相关词汇数量
                            break
            
            result['related_words'] = list(related_words)[:8]
            
            # 尝试提取演变路径
            if full_etymology:
                evolution_matches = re.findall(r'(\d{2,4})\s*[cs]?\s*\.?\s*,?\s*([^,;]+)', full_etymology)
                result['evolution_path'] = [{'period': match[0], 'form': match[1].strip()} 
                                          for match in evolution_matches[:5]]
            
            return result
            
        except Exception as e:
            print(f"   Warning: Could not fetch etymology from Etymonline for '{word}': {e}")
            return {
                'etymology_history': '',
                'root_meaning': '',
                'related_words': [],
                'language_origin': '',
                'evolution_path': []
            }
    
    def fetch_cambridge_examples(self, word: str) -> List[str]:
        """从Cambridge Dictionary获取例句 - 保持向后兼容"""
        info = self.fetch_cambridge_dictionary_info(word)
        return info['examples']
    
    def extract_vocabulary(self, text: str) -> List[Tuple[str, str, int]]:
        """从文本中提取词汇，返回(单词, CEFR级别, 频次)的列表"""
        # 分词和词性标注
        tokens = word_tokenize(text.lower())
        tagged = pos_tag(tokens)
        
        # 过滤词汇
        vocabulary = []
        word_freq = Counter()
        
        # 确定目标学习级别范围
        target_levels = self._get_target_learning_levels()
        
        for word, pos in tagged:
            # 基础过滤条件
            if (len(word) >= 4 and  # 最小长度要求
                word not in self.stop_words and 
                word not in self.basic_words and  # 过滤已掌握的基础词汇
                word.isalpha() and
                not word.isupper() and  # 避免全大写缩略词
                not self._is_proper_noun(word) and  # 过滤专有名词
                pos in ['NN', 'NNS', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'JJ', 'JJR', 'JJS', 'RB', 'RBR', 'RBS']):
                
                # 获取CEFR级别
                cefr_level = self.cefr_vocab.get_level_for_word(word)
                
                # 只保留目标学习级别的词汇
                if cefr_level in target_levels:
                    # 额外检查：确保不是过于简单的词汇变形
                    if not self._is_too_simple_variation(word):
                        word_freq[word] += 1
        
        # 转换为列表并按频次和CEFR级别排序
        vocabulary_items = []
        level_priority = {'B2': 3, 'C1': 2, 'C2': 1, 'B1': 4}  # 优先级权重
        
        for word, freq in word_freq.most_common():
            cefr_level = self.cefr_vocab.get_level_for_word(word)
            # 计算重要性得分（频次 + 级别权重）
            priority_weight = level_priority.get(cefr_level, 0)
            importance_score = freq + priority_weight
            vocabulary_items.append((word, cefr_level, freq, importance_score))
        
        # 按重要性得分排序
        vocabulary_items.sort(key=lambda x: x[3], reverse=True)
        
        # 返回格式：(单词, CEFR级别, 频次)
        return [(word, cefr_level, freq) for word, cefr_level, freq, _ in vocabulary_items]
    
    def _get_target_learning_levels(self) -> List[str]:
        """根据当前水平确定目标学习级别"""
        level_progression = {
            'A1': ['A2', 'B1'],
            'A2': ['B1', 'B2'],
            'B1': ['B2', 'C1'],
            'B1+': ['B2', 'C1'],  # B1+学习者应该学习B2和C1词汇
            'B2': ['C1', 'C2'],
            'C1': ['C2'],
            'C2': ['C2']  # 已经最高级
        }
        
        return level_progression.get(self.target_level, ['B2', 'C1'])
    
    def _is_too_simple_variation(self, word: str) -> bool:
        """检查是否为过于简单的词汇变形"""
        word_lower = word.lower()
        
        # 检查是否为基础词的简单变形
        if word_lower.endswith('ing'):
            base_word = word_lower[:-3]
            if base_word in self.basic_words:
                return True
        
        if word_lower.endswith('ed'):
            base_word = word_lower[:-2]
            if base_word in self.basic_words:
                return True
        
        if word_lower.endswith('er'):
            base_word = word_lower[:-2]
            if base_word in self.basic_words:
                return True
        
        if word_lower.endswith('ly'):
            base_word = word_lower[:-2]
            if base_word in self.basic_words:
                return True
        
        if word_lower.endswith('s'):
            base_word = word_lower[:-1]
            if base_word in self.basic_words:
                return True
        
        return False
    
    def _is_proper_noun(self, word: str) -> bool:
        """检查是否为专有名词（地名、人名等）"""
        # 专有名词通常首字母大写，且可能包含多个大写字母
        if word[0].isupper():
            # 常见的地名、国家、城市等
            proper_nouns = {
                'shanghai', 'beijing', 'china', 'america', 'europe', 'asia', 'africa', 'russia', 
                'japan', 'india', 'canada', 'australia', 'brazil', 'mexico', 'germany', 
                'france', 'italy', 'spain', 'london', 'paris', 'tokyo', 'moscow', 'delhi',
                'washington', 'california', 'texas', 'florida', 'york', 'trump', 'biden',
                'obama', 'clinton', 'bush', 'reagan', 'kennedy', 'roosevelt', 'lincoln'
            }
            if word.lower() in proper_nouns:
                return True
        return False
    
    def analyze_sentence_difficulty(self, sentence: str) -> Dict:
        """分析句子的复杂度和难点"""
        analysis = {
            'sentence': sentence.strip(),
            'length': len(sentence.split()),
            'difficulty_score': 0,
            'complexity_factors': [],
            'grammar_patterns': [],
            'difficult_words': [],
            'explanation': '',
            'simplified_version': ''
        }
        
        # 基础长度分析
        word_count = len(sentence.split())
        if word_count > 20:
            analysis['complexity_factors'].append('Long sentence (20+ words)')
            analysis['difficulty_score'] += 2
        elif word_count > 15:
            analysis['complexity_factors'].append('Medium-length sentence (15-20 words)')
            analysis['difficulty_score'] += 1
        
        # 词汇复杂度分析
        tokens = word_tokenize(sentence.lower())
        for token in tokens:
            if len(token) > 8 and token.isalpha():
                difficulty = self.analyze_word_difficulty(token)
                if difficulty in ['advanced', 'expert']:
                    analysis['difficult_words'].append(token)
                    analysis['difficulty_score'] += 1
        
        # 语法结构分析
        tagged = pos_tag(word_tokenize(sentence))
        analysis['grammar_patterns'] = self._identify_grammar_patterns(tagged)
        
        # 句子类型判断
        sentence_types = self._classify_sentence_type(sentence, tagged)
        analysis['complexity_factors'].extend(sentence_types)
        
        # 难度评级
        if analysis['difficulty_score'] >= 6:
            analysis['difficulty_level'] = 'Expert'
        elif analysis['difficulty_score'] >= 4:
            analysis['difficulty_level'] = 'Advanced'
        elif analysis['difficulty_score'] >= 2:
            analysis['difficulty_level'] = 'Intermediate'
        else:
            analysis['difficulty_level'] = 'Basic'
        
        # 生成解释和简化版本
        analysis['explanation'] = self._explain_sentence_complexity(analysis)
        analysis['simplified_version'] = self._simplify_sentence(sentence)
        
        return analysis
    
    def _identify_grammar_patterns(self, tagged_words: List[Tuple[str, str]]) -> List[str]:
        """识别语法结构模式"""
        patterns = []
        pos_sequence = [tag for word, tag in tagged_words]
        
        # 被动语态
        if any(tag in ['VBN', 'VBZ'] for tag in pos_sequence):
            for i, tag in enumerate(pos_sequence):
                if tag in ['VBZ', 'VBP', 'VBD'] and i < len(pos_sequence) - 1:
                    if pos_sequence[i + 1] == 'VBN':
                        patterns.append('Passive voice')
                        break
        
        # 复杂时态
        if 'MD' in pos_sequence:  # Modal verbs
            patterns.append('Modal verbs')
        
        # 从句识别
        subordinating_conjunctions = ['that', 'which', 'who', 'where', 'when', 'while', 'although', 'because', 'since', 'if', 'unless']
        words = [word.lower() for word, tag in tagged_words]
        
        for conjunction in subordinating_conjunctions:
            if conjunction in words:
                patterns.append(f'Subordinate clause ({conjunction})')
                break
        
        # 复合句识别
        coordinating_conjunctions = ['and', 'but', 'or', 'so', 'yet']
        for conjunction in coordinating_conjunctions:
            if conjunction in words:
                patterns.append(f'Compound sentence ({conjunction})')
                break
        
        # 形容词从句
        if 'WDT' in pos_sequence or 'WP' in pos_sequence:
            patterns.append('Relative clause')
        
        # 分词结构
        if 'VBG' in pos_sequence or 'VBN' in pos_sequence:
            patterns.append('Participle construction')
        
        return patterns
    
    def _classify_sentence_type(self, sentence: str, tagged_words: List[Tuple[str, str]]) -> List[str]:
        """分类句子类型"""
        types = []
        
        # 疑问句
        if sentence.strip().endswith('?'):
            types.append('Question')
        
        # 感叹句
        if sentence.strip().endswith('!'):
            types.append('Exclamation')
        
        # 条件句
        conditional_markers = ['if', 'unless', 'provided', 'supposing', 'assuming']
        words = [word.lower() for word, tag in tagged_words]
        
        for marker in conditional_markers:
            if marker in words:
                types.append('Conditional sentence')
                break
        
        # 比较句
        comparative_markers = ['than', 'as...as', 'more', 'less', 'better', 'worse']
        for marker in comparative_markers:
            if marker in ' '.join(words):
                types.append('Comparative sentence')
                break
        
        return types
    
    def _explain_sentence_complexity(self, analysis: Dict) -> str:
        """生成句子复杂度解释"""
        explanations = []
        
        if analysis['length'] > 20:
            explanations.append(f"长句子({analysis['length']}个单词)需要注意句子结构")
        
        if analysis['difficult_words']:
            explanations.append(f"包含高级词汇: {', '.join(analysis['difficult_words'][:3])}")
        
        if analysis['grammar_patterns']:
            explanations.append(f"复杂语法结构: {', '.join(analysis['grammar_patterns'][:2])}")
        
        return '; '.join(explanations) if explanations else "相对简单的句子结构"
    
    def _simplify_sentence(self, sentence: str) -> str:
        """尝试简化句子（基础版本）"""
        # 这是一个简化的实现，实际应用中需要更复杂的NLP处理
        simplified = sentence
        
        # 移除一些复杂的从句标记词并简化
        complex_phrases = {
            'In spite of the fact that': 'Although',
            'Due to the fact that': 'Because',
            'It is important to note that': '',
            'What is particularly interesting is that': 'Notably,',
            'It should be emphasized that': '',
        }
        
        for complex_phrase, simple_phrase in complex_phrases.items():
            simplified = simplified.replace(complex_phrase, simple_phrase)
        
        return simplified.strip()
    
    def extract_difficult_sentences(self, text: str, min_difficulty: str = 'Intermediate') -> List[Dict]:
        """从文本中提取难句"""
        sentences = sent_tokenize(text)
        difficult_sentences = []
        
        difficulty_levels = {'Basic': 1, 'Intermediate': 2, 'Advanced': 3, 'Expert': 4}
        min_score = difficulty_levels.get(min_difficulty, 2)
        
        for sentence in sentences:
            # 过滤太短或太简单的句子
            if len(sentence.split()) < 8:
                continue
                
            analysis = self.analyze_sentence_difficulty(sentence)
            sentence_score = difficulty_levels.get(analysis['difficulty_level'], 1)
            
            if sentence_score >= min_score:
                difficult_sentences.append(analysis)
        
        # 按难度排序，选取最有代表性的句子
        difficult_sentences.sort(key=lambda x: x['difficulty_score'], reverse=True)
        
        return difficult_sentences[:20]  # 返回前20个最难的句子
    
    def generate_word_explanation(self, word: str) -> Dict:
        """生成单词的详细解释 - 优先使用在线词典信息"""
        # 首先尝试从Cambridge Dictionary获取信息
        cambridge_info = self.fetch_cambridge_dictionary_info(word)
        
        explanation = {
            'word': word.lower(),  # 单词改为小写显示
            'pronunciation': cambridge_info['pronunciation'] or self.get_pronunciation(word),
            'difficulty': self.analyze_word_difficulty(word),
            'etymology': self._get_enhanced_etymology(word, cambridge_info),
            'definitions': self._get_definitions(word),
            'related_words': self._find_related_words(word),
            'examples': self._generate_examples(word),
            'part_of_speech': cambridge_info['part_of_speech'] or self._get_part_of_speech(word)
        }
        return explanation
    
    def _get_enhanced_etymology(self, word: str, cambridge_info: Dict) -> Dict:
        """获取增强的词根词缀信息"""
        # 首先使用本地词根词缀分析
        etymology = self._analyze_etymology(word)
        
        # 从Etymology Online获取详细词源信息
        online_etymology = self.fetch_etymology_from_etymonline(word)
        if online_etymology and online_etymology.get('etymology_history'):
            etymology.update({
                'etymology_history': online_etymology['etymology_history'],
                'root_meaning': online_etymology['root_meaning'],
                'related_words': online_etymology['related_words'],
                'language_origin': online_etymology['language_origin'],
                'evolution_path': online_etymology['evolution_path']
            })
        
        # 如果Cambridge有词源信息，也加入
        if cambridge_info.get('etymology'):
            etymology['cambridge_etymology'] = cambridge_info['etymology']
        
        return etymology
    
    def _analyze_etymology(self, word: str) -> Dict:
        """分析词汇的词根词缀"""
        etymology = {'roots': [], 'prefixes': [], 'suffixes': []}
        
        word_lower = word.lower()
        
        # 检查前缀
        for prefix, meaning in self.vocabulary_database['prefixes'].items():
            prefix_clean = prefix.replace('-', '')
            if word_lower.startswith(prefix_clean):
                etymology['prefixes'].append({'affix': prefix, 'meaning': meaning})
        
        # 检查后缀
        for suffix, meaning in self.vocabulary_database['suffixes'].items():
            suffix_clean = suffix.replace('-', '')
            if word_lower.endswith(suffix_clean):
                etymology['suffixes'].append({'affix': suffix, 'meaning': meaning})
        
        # 检查词根（简化版）
        for root, info in self.vocabulary_database['roots'].items():
            if root in word_lower:
                etymology['roots'].append({'root': root, 'meaning': info['meaning']})
        
        return etymology
    
    def _get_definitions(self, word: str) -> List[str]:
        """获取单词定义"""
        definitions = []
        synsets = wordnet.synsets(word)
        
        if synsets:
            # 获取前3个最常见的定义
            for synset in synsets[:3]:
                definitions.append(synset.definition())
        else:
            definitions.append("Definition not found in WordNet")
        
        return definitions
    
    def _find_related_words(self, word: str) -> Dict:
        """查找相关词汇（同根词、同义词等）"""
        related = {'synonyms': [], 'family': []}
        
        # 查找同义词
        synsets = wordnet.synsets(word)
        for synset in synsets[:2]:  # 限制数量
            for lemma in synset.lemmas()[:3]:
                if lemma.name() != word and lemma.name() not in related['synonyms']:
                    related['synonyms'].append(lemma.name().replace('_', ' '))
        
        # 查找词汇家族（基于词根）
        etymology = self._analyze_etymology(word)
        for root_info in etymology['roots']:
            root = root_info['root']
            if root in self.vocabulary_database['roots']:
                examples = self.vocabulary_database['roots'][root]['examples']
                for example in examples:
                    if example != word and example not in related['family']:
                        related['family'].append(example)
        
        return related
    
    def _generate_examples(self, word: str) -> List[str]:
        """生成高质量例句 - 优先使用原文，然后使用Cambridge Dictionary"""
        examples = []
        
        # 方法1: 从原文中提取例句
        source_examples = self.extract_sentences_from_source(word)
        examples.extend(source_examples)
        
        # 方法2: 如果原文例句不够，从Cambridge Dictionary获取
        if len(examples) < 3:
            cambridge_examples = self.fetch_cambridge_examples(word)
            examples.extend(cambridge_examples)
        
        # 如果仍然不够，使用改进的备用例句
        if len(examples) < 3:
            fallback_examples = self._generate_fallback_examples(word)
            examples.extend(fallback_examples)
        
        # 去重并返回前3个
        unique_examples = []
        for example in examples:
            if example not in unique_examples:
                unique_examples.append(example)
        
        return unique_examples[:3]
    
    def _generate_fallback_examples(self, word: str) -> List[str]:
        """生成改进的备用例句"""
        synsets = wordnet.synsets(word)
        word_lower = word.lower()
        
        if synsets:
            pos = synsets[0].pos()
            
            if pos == 'v':  # 动词
                return [
                    f"Companies need to {word} their strategies regularly.",
                    f"It's essential to {word} these principles effectively.",
                    f"Successful leaders know how to {word} in difficult situations."
                ]
            elif pos == 'a':  # 形容词
                return [
                    f"The {word} approach has proven successful in many cases.",
                    f"This {word} method addresses the core issues effectively.",
                    f"Experts recommend taking a more {word} stance on this matter."
                ]
            elif pos == 'n':  # 名词
                return [
                    f"The concept of {word} is fundamental to this field.",
                    f"Recent research has examined the role of {word} in society.",
                    f"Understanding {word} is crucial for academic success."
                ]
        
        # 默认通用例句
        return [
            f"The importance of {word} cannot be understated in this context.",
            f"Researchers continue to study {word} and its implications.",
            f"Modern society must consider the impact of {word} carefully."
        ]
    
    def create_study_guide(self, vocabulary: List[Tuple[str, str, int]], 
                          source_file: str, max_words: int = 40, text: str = "") -> str:
        """创建基于CEFR标准的词汇学习指南"""
        
        # 按CEFR级别和频次分组
        level_groups = {'B2': [], 'C1': [], 'C2': [], 'B1': []}
        
        for word, cefr_level, freq in vocabulary[:max_words]:
            if cefr_level in level_groups:
                level_groups[cefr_level].append((word, freq))
        
        # 确定目标级别范围
        target_levels = self._get_target_learning_levels()
        current_level = self.target_level
        
        # 生成学习指南内容
        guide_content = f"""📚 CEFR-Based Vocabulary Study Guide
当前水平: {current_level} | 目标学习级别: {' & '.join(target_levels)}

源文件: {source_file}

==============================================================

🔤 VOCABULARY LIST ORGANIZED BY CEFR LEVELS

"""
        
        # 按CEFR级别组织词汇展示
        word_count = 1
        
        # 按优先级顺序展示各级别词汇
        priority_levels = ['C1', 'B2', 'C2', 'B1']  # C1优先，因为是主要目标
        
        for level in priority_levels:
            if level_groups[level]:
                guide_content += f"\n🎯 {level} Level Words ({len(level_groups[level])} words)\n"
                guide_content += "=" * 50 + "\n\n"
                
                for word, freq in level_groups[level]:
                    explanation = self.generate_word_explanation(word)
                    
                    guide_content += f"""{word_count}. {explanation['word']} {explanation['pronunciation']} [{level}]
【出现频次】{freq} 次
【词根词缀】{self._format_etymology(explanation['etymology'])}
【词性】{explanation['part_of_speech']}
【释义】{explanation['definitions'][0] if explanation['definitions'] else 'Definition not available'}
【同根词】{', '.join(explanation['related_words']['family'][:3]) if explanation['related_words']['family'] else 'No related words found'}
【例句】
"""
                    
                    for i, example in enumerate(explanation['examples'], 1):
                        guide_content += f"- {example}\n"
                    
                    guide_content += "\n"
                    word_count += 1
        
        # 添加CEFR级别统计
        guide_content += f"""
==============================================================

📊 CEFR LEVEL DISTRIBUTION
这些词汇按CEFR级别分布统计：

🟦 C1 ADVANCED ({len(level_groups['C1'])} words) - 高级词汇，提升学术和专业表达
{', '.join([word for word, freq in level_groups['C1'][:10]])}

🟨 B2 UPPER-INTERMEDIATE ({len(level_groups['B2'])} words) - 中高级词汇，日常和工作必备
{', '.join([word for word, freq in level_groups['B2'][:10]])}

🟪 C2 PROFICIENCY ({len(level_groups['C2'])} words) - 接近母语者水平的高难词汇
{', '.join([word for word, freq in level_groups['C2'][:5]])}

==============================================================

📝 DIFFICULT SENTENCES ANALYSIS
以下是文本中的复杂句子，需要特别注意语法结构和理解难点：

"""
        
        # 添加难句分析
        if text:
            difficult_sentences = self.extract_difficult_sentences(text, 'Intermediate')
            
            for i, sentence_analysis in enumerate(difficult_sentences[:10], 1):
                guide_content += f"""
{i}. 【{sentence_analysis['difficulty_level']}】 {sentence_analysis['sentence']}

   📊 复杂度分析:
   - 句子长度: {sentence_analysis['length']} 个单词
   - 难度评分: {sentence_analysis['difficulty_score']}/10
   - 复杂因素: {', '.join(sentence_analysis['complexity_factors']) if sentence_analysis['complexity_factors'] else '无特殊复杂因素'}
   
   🔍 语法结构: {', '.join(sentence_analysis['grammar_patterns']) if sentence_analysis['grammar_patterns'] else '基础语法结构'}
   
   💡 理解要点: {sentence_analysis['explanation']}
   
   ✏️  简化理解: {sentence_analysis['simplified_version']}

"""
        
        guide_content += f"""
==============================================================

💡 STUDY TIPS

**词汇学习策略:**
1. **词根记忆法**: 重点关注词根词缀，如 -crat (统治), auto- (自己), -ism (主义)
2. **语境学习**: 结合音频内容理解词汇在讨论中的使用
3. **同义替换**: 学习高级词汇替换基础词汇
4. **写作应用**: 这些词汇特别适用于学术写作和正式讨论

**句子理解技巧:**
1. **结构分析**: 先找主谓宾，再分析从句和修饰成分
2. **断句练习**: 长句子可以按照语法结构进行断句理解
3. **语法模式**: 熟悉常见的复杂语法结构（被动语态、从句等）
4. **简化对比**: 对照简化版本理解复杂句子的核心意思

==============================================================

🎯 RECOMMENDED NEXT STEPS

**词汇提升:**
1. 听原音频，注意这些词汇的发音和语调
2. 制作单词卡片，正面写词汇，反面写释义和例句
3. 尝试用这些词汇写一篇相关主题的短文
4. 定期复习，特别关注高优先级词汇

**句子分析:**
1. 每天分析2-3个复杂句子，理解其语法结构
2. 练习长句子的断句和理解
3. 尝试改写复杂句子为简单句子
4. 在写作中模仿这些高级句型结构

Generated by CEFR-Based Vocabulary & Sentence Analysis Tool
Current Level: {self.target_level} | Target Learning Levels: {' & '.join(target_levels)}
Total Vocabulary Analyzed: {len(vocabulary)} words
Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return guide_content
    
    def _format_etymology(self, etymology: Dict) -> str:
        """格式化词源信息"""
        parts = []
        
        # 在线词源历史（优先显示）
        if etymology.get('etymology_history'):
            parts.append(f"📜 词源历史: {etymology['etymology_history']}")
        
        # 语言起源
        if etymology.get('language_origin'):
            parts.append(f"🌍 语言起源: {etymology['language_origin']}")
        
        # 词根含义
        if etymology.get('root_meaning'):
            parts.append(f"🔤 词根含义: {etymology['root_meaning']}")
        
        # 演变路径
        if etymology.get('evolution_path') and etymology['evolution_path']:
            evolution_str = " → ".join([f"{e['period']}: {e['form']}" for e in etymology['evolution_path']])
            parts.append(f"📈 演变路径: {evolution_str}")
        
        # 相关同根词
        if etymology.get('related_words') and etymology['related_words']:
            related_str = ', '.join(etymology['related_words'])
            parts.append(f"🔗 同根词汇: {related_str}")
        
        # 本地词缀分析（作为补充）
        local_parts = []
        if etymology.get('prefixes'):
            local_parts.extend([f"{p['affix']} ({p['meaning']})" for p in etymology['prefixes']])
        
        if etymology.get('roots'):
            local_parts.extend([f"{r['root']}- ({r['meaning']})" for r in etymology['roots']])
        
        if etymology.get('suffixes'):
            local_parts.extend([f"{s['affix']} ({s['meaning']})" for s in etymology['suffixes']])
        
        if local_parts:
            parts.append(f"🧩 词缀分析: {' + '.join(local_parts)}")
        
        return '\n'.join(parts) if parts else 'Etymology not available'
    
    def _get_part_of_speech(self, word: str) -> str:
        """获取词性"""
        synsets = wordnet.synsets(word)
        if synsets:
            pos_mapping = {
                'n': 'noun',
                'v': 'verb', 
                'a': 'adjective',
                's': 'adjective',
                'r': 'adverb'
            }
            return pos_mapping.get(synsets[0].pos(), 'unknown')
        return 'unknown'
    
    def analyze_transcript_file(self, file_path: Path, output_dir: Optional[Path] = None) -> Path:
        """分析转录文件并生成词汇学习指南"""
        print(f"📖 分析转录文件: {file_path.name}")
        
        # 提取文本
        text = self.extract_text_from_transcript(file_path)
        if not text:
            raise ValueError("无法从文件中提取文本")
        
        print(f"✅ 提取文本长度: {len(text)} 字符")
        
        # 提取词汇
        print("🔍 提取和分析词汇...")
        vocabulary = self.extract_vocabulary(text)
        
        print(f"✅ 识别出 {len(vocabulary)} 个适合学习的词汇")
        
        # 生成学习指南
        print("📝 生成词汇和句子学习指南...")
        guide_content = self.create_study_guide(vocabulary, file_path.name, max_words=40, text=text)
        
        # 保存文件
        if output_dir is None:
            output_dir = file_path.parent
        
        output_file = output_dir / f"{file_path.stem}_Vocabulary_Study.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"💾 学习指南已保存: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description='分析音频转录文件并生成词汇学习指南',
        epilog='支持从podcast转录文件中提取适合特定英语水平的词汇进行学习'
    )
    
    parser.add_argument('input', help='输入的转录文件路径')
    parser.add_argument('-o', '--output', help='输出目录 (默认: 与输入文件同目录)')
    parser.add_argument('-l', '--level', default='6.0-6.5', 
                       help='目标英语水平 (默认: 6.0-6.5)')
    parser.add_argument('-m', '--max-words', type=int, default=40,
                       help='最大词汇数量 (默认: 40)')
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    
    if not input_file.exists():
        print(f"❌ 输入文件不存在: {input_file}")
        sys.exit(1)
    
    if not input_file.suffix.lower() == '.txt':
        print(f"❌ 只支持.txt格式的转录文件")
        sys.exit(1)
    
    output_dir = Path(args.output) if args.output else None
    
    try:
        # 初始化分析器
        print(f"🚀 初始化词汇分析器 (目标水平: {args.level})")
        analyzer = VocabularyAnalyzer(args.level)
        
        # 分析文件
        result_file = analyzer.analyze_transcript_file(
            input_file, 
            output_dir
        )
        
        print(f"\n🎉 词汇分析完成!")
        print(f"📁 学习指南文件: {result_file}")
        print(f"💡 建议结合原音频文件进行学习，效果更佳!")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()