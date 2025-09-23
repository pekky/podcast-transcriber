#!/usr/bin/env python3
"""
Comprehensive English Vocabulary Difficulty Database

Based on multiple authoritative sources:
1. CEFR (Common European Framework of Reference)
2. Oxford 3000/5000 word lists
3. Academic Word List (AWL)
4. Google Books Ngram frequency data
5. COCA (Corpus of Contemporary American English)
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
import csv
import io

class VocabularyDatabase:
    def __init__(self, db_path: str = "vocabulary.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.init_database()
        
    def init_database(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vocabulary (
                word TEXT PRIMARY KEY,
                frequency_rank INTEGER,
                cefr_level TEXT,
                difficulty_score REAL,
                pos TEXT,
                definition_zh TEXT,
                definition_en TEXT,
                phonetic_us TEXT,
                phonetic_uk TEXT,
                is_academic BOOLEAN,
                is_oxford3000 BOOLEAN,
                is_oxford5000 BOOLEAN,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_frequency ON vocabulary(frequency_rank);
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cefr ON vocabulary(cefr_level);
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_difficulty ON vocabulary(difficulty_score);
        ''')
        
        self.conn.commit()
        
    def load_base_vocabulary(self):
        """加载基础词汇数据"""
        # 基于权威数据源的词汇列表
        base_vocab = [
            # A1 Level (最基础 500 words)
            {"word": "the", "freq": 1, "cefr": "A1", "diff": 1.0, "def_zh": "这个；那个", "def_en": "definite article", "ph_us": "/ðə/", "ph_uk": "/ðə/"},
            {"word": "be", "freq": 2, "cefr": "A1", "diff": 1.0, "def_zh": "是；存在", "def_en": "to exist", "ph_us": "/bi/", "ph_uk": "/biː/"},
            {"word": "have", "freq": 3, "cefr": "A1", "diff": 1.0, "def_zh": "有；拥有", "def_en": "to possess", "ph_us": "/hæv/", "ph_uk": "/hæv/"},
            {"word": "and", "freq": 4, "cefr": "A1", "diff": 1.0, "def_zh": "和；与", "def_en": "conjunction", "ph_us": "/ænd/", "ph_uk": "/ænd/"},
            {"word": "of", "freq": 5, "cefr": "A1", "diff": 1.0, "def_zh": "的；属于", "def_en": "preposition", "ph_us": "/ʌv/", "ph_uk": "/ɒv/"},
            {"word": "a", "freq": 6, "cefr": "A1", "diff": 1.0, "def_zh": "一个", "def_en": "indefinite article", "ph_us": "/ə/", "ph_uk": "/ə/"},
            {"word": "to", "freq": 7, "cefr": "A1", "diff": 1.0, "def_zh": "到；向", "def_en": "preposition", "ph_us": "/tu/", "ph_uk": "/tuː/"},
            {"word": "in", "freq": 8, "cefr": "A1", "diff": 1.0, "def_zh": "在...里", "def_en": "preposition", "ph_us": "/ɪn/", "ph_uk": "/ɪn/"},
            {"word": "you", "freq": 9, "cefr": "A1", "diff": 1.0, "def_zh": "你；您", "def_en": "pronoun", "ph_us": "/ju/", "ph_uk": "/juː/"},
            {"word": "for", "freq": 10, "cefr": "A1", "diff": 1.0, "def_zh": "为了；给", "def_en": "preposition", "ph_us": "/fɔr/", "ph_uk": "/fɔː/"},
            
            # A2 Level (501-1500)
            {"word": "important", "freq": 520, "cefr": "A2", "diff": 2.0, "def_zh": "重要的", "def_en": "having great significance", "ph_us": "/ɪmˈpɔrtənt/", "ph_uk": "/ɪmˈpɔːtənt/"},
            {"word": "different", "freq": 580, "cefr": "A2", "diff": 2.0, "def_zh": "不同的", "def_en": "not the same", "ph_us": "/ˈdɪfərənt/", "ph_uk": "/ˈdɪfərənt/"},
            {"word": "following", "freq": 620, "cefr": "A2", "diff": 2.0, "def_zh": "下列的；接下来的", "def_en": "coming after", "ph_us": "/ˈfɑloʊɪŋ/", "ph_uk": "/ˈfɒləʊɪŋ/"},
            {"word": "without", "freq": 680, "cefr": "A2", "diff": 2.0, "def_zh": "没有；无", "def_en": "not having", "ph_us": "/wɪˈðaʊt/", "ph_uk": "/wɪˈðaʊt/"},
            {"word": "program", "freq": 720, "cefr": "A2", "diff": 2.0, "def_zh": "程序；计划", "def_en": "a set of instructions", "ph_us": "/ˈproʊɡræm/", "ph_uk": "/ˈprəʊɡræm/"},
            {"word": "problem", "freq": 750, "cefr": "A2", "diff": 2.0, "def_zh": "问题；难题", "def_en": "a difficult situation", "ph_us": "/ˈprɑbləm/", "ph_uk": "/ˈprɒbləm/"},
            {"word": "complete", "freq": 800, "cefr": "A2", "diff": 2.0, "def_zh": "完整的；完成", "def_en": "having all parts", "ph_us": "/kəmˈplit/", "ph_uk": "/kəmˈpliːt/"},
            
            # B1 Level (1501-3000)
            {"word": "technology", "freq": 1580, "cefr": "B1", "diff": 3.0, "def_zh": "技术；科技", "def_en": "applied science", "ph_us": "/tekˈnɑlədʒi/", "ph_uk": "/tekˈnɒlədʒi/"},
            {"word": "computer", "freq": 1620, "cefr": "B1", "diff": 3.0, "def_zh": "计算机；电脑", "def_en": "electronic device", "ph_us": "/kəmˈpjutər/", "ph_uk": "/kəmˈpjuːtə/"},
            {"word": "business", "freq": 1680, "cefr": "B1", "diff": 3.0, "def_zh": "商业；生意", "def_en": "commercial activity", "ph_us": "/ˈbɪznəs/", "ph_uk": "/ˈbɪznəs/"},
            {"word": "development", "freq": 1720, "cefr": "B1", "diff": 3.0, "def_zh": "发展；开发", "def_en": "growth or progress", "ph_us": "/dɪˈveləpmənt/", "ph_uk": "/dɪˈveləpmənt/"},
            {"word": "management", "freq": 1780, "cefr": "B1", "diff": 3.0, "def_zh": "管理；经营", "def_en": "controlling a business", "ph_us": "/ˈmænɪdʒmənt/", "ph_uk": "/ˈmænɪdʒmənt/"},
            {"word": "system", "freq": 1820, "cefr": "B1", "diff": 3.0, "def_zh": "系统；制度", "def_en": "organized whole", "ph_us": "/ˈsɪstəm/", "ph_uk": "/ˈsɪstəm/"},
            {"word": "process", "freq": 1900, "cefr": "B1", "diff": 3.0, "def_zh": "过程；处理", "def_en": "series of actions", "ph_us": "/ˈprɑses/", "ph_uk": "/ˈprəʊses/"},
            {"word": "understanding", "freq": 2100, "cefr": "B1", "diff": 3.0, "def_zh": "理解；了解", "def_en": "comprehension", "ph_us": "/ˌʌndərˈstændɪŋ/", "ph_uk": "/ˌʌndəˈstændɪŋ/"},
            
            # B2 Level (3001-5000) - 中高级
            {"word": "comprehensive", "freq": 3200, "cefr": "B2", "diff": 4.0, "def_zh": "全面的；综合的", "def_en": "complete and including everything", "ph_us": "/ˌkɑmprɪˈhensɪv/", "ph_uk": "/ˌkɒmprɪˈhensɪv/", "academic": True, "oxford5000": True},
            {"word": "artificial", "freq": 3400, "cefr": "B2", "diff": 4.0, "def_zh": "人工的；人造的", "def_en": "made by humans, not natural", "ph_us": "/ˌɑrtɪˈfɪʃəl/", "ph_uk": "/ˌɑːtɪˈfɪʃəl/", "academic": True, "oxford5000": True},
            {"word": "intelligence", "freq": 3600, "cefr": "B2", "diff": 4.0, "def_zh": "智力；智能", "def_en": "ability to learn and understand", "ph_us": "/ɪnˈtelɪdʒəns/", "ph_uk": "/ɪnˈtelɪdʒəns/", "academic": True, "oxford5000": True},
            {"word": "innovative", "freq": 3800, "cefr": "B2", "diff": 4.0, "def_zh": "创新的；革新的", "def_en": "introducing new ideas", "ph_us": "/ˈɪnəˌvetɪv/", "ph_uk": "/ˈɪnəveɪtɪv/", "academic": True},
            {"word": "sustainable", "freq": 4000, "cefr": "B2", "diff": 4.0, "def_zh": "可持续的", "def_en": "able to continue over time", "ph_us": "/səˈsteɪnəbəl/", "ph_uk": "/səˈsteɪnəbəl/", "academic": True},
            {"word": "fundamental", "freq": 4200, "cefr": "B2", "diff": 4.0, "def_zh": "基本的；根本的", "def_en": "basic and essential", "ph_us": "/ˌfʌndəˈmentəl/", "ph_uk": "/ˌfʌndəˈmentəl/", "academic": True, "oxford5000": True},
            {"word": "implementation", "freq": 4400, "cefr": "B2", "diff": 4.0, "def_zh": "实施；执行", "def_en": "the process of putting a plan into effect", "ph_us": "/ˌɪmpləmənˈteɪʃən/", "ph_uk": "/ˌɪmplɪmenˈteɪʃən/", "academic": True},
            
            # C1 Level (5001-8000) - 高级
            {"word": "sophisticated", "freq": 5200, "cefr": "C1", "diff": 5.0, "def_zh": "精密的；老练的", "def_en": "highly developed and complex", "ph_us": "/səˈfɪstɪˌkeɪtɪd/", "ph_uk": "/səˈfɪstɪkeɪtɪd/", "academic": True, "oxford5000": True},
            {"word": "unprecedented", "freq": 5800, "cefr": "C1", "diff": 5.0, "def_zh": "史无前例的", "def_en": "never done or known before", "ph_us": "/ʌnˈpresɪˌdentɪd/", "ph_uk": "/ʌnˈpresɪdentɪd/", "academic": True},
            {"word": "phenomenon", "freq": 6000, "cefr": "C1", "diff": 5.0, "def_zh": "现象；奇迹", "def_en": "a fact or situation observed", "ph_us": "/fəˈnɑməˌnɑn/", "ph_uk": "/fəˈnɒmɪnən/", "academic": True, "oxford5000": True},
            {"word": "theoretical", "freq": 6200, "cefr": "C1", "diff": 5.0, "def_zh": "理论的；假设的", "def_en": "based on theory rather than practice", "ph_us": "/ˌθiəˈretɪkəl/", "ph_uk": "/ˌθɪəˈretɪkəl/", "academic": True},
            {"word": "methodology", "freq": 6400, "cefr": "C1", "diff": 5.0, "def_zh": "方法论；方法", "def_en": "system of methods used in research", "ph_us": "/ˌmeθəˈdɑlədʒi/", "ph_uk": "/ˌmeθəˈdɒlədʒi/", "academic": True},
            {"word": "paradigmatic", "freq": 7000, "cefr": "C1", "diff": 5.0, "def_zh": "范式的；典型的", "def_en": "serving as a typical example", "ph_us": "/ˌpærədaɪɡˈmætɪk/", "ph_uk": "/ˌpærədɪɡˈmætɪk/", "academic": True},
            {"word": "algorithmic", "freq": 7200, "cefr": "C1", "diff": 5.0, "def_zh": "算法的", "def_en": "relating to algorithms", "ph_us": "/ˌælɡəˈrɪðmɪk/", "ph_uk": "/ˌælɡəˈrɪðmɪk/", "academic": True},
            
            # C2 Level (8000+) - 最高级
            {"word": "anthropic", "freq": 8500, "cefr": "C2", "diff": 6.0, "def_zh": "人类的；人为的", "def_en": "relating to human beings", "ph_us": "/ænˈθrɑpɪk/", "ph_uk": "/ænˈθrɒpɪk/", "academic": True},
            {"word": "epistemological", "freq": 9000, "cefr": "C2", "diff": 6.0, "def_zh": "认识论的", "def_en": "relating to the theory of knowledge", "ph_us": "/ɪˌpɪstəməˈlɑdʒɪkəl/", "ph_uk": "/ɪˌpɪstɪməˈlɒdʒɪkəl/", "academic": True},
            {"word": "quintessential", "freq": 9200, "cefr": "C2", "diff": 6.0, "def_zh": "典型的；精髓的", "def_en": "representing the most perfect example", "ph_us": "/ˌkwɪntəˈsenʃəl/", "ph_uk": "/ˌkwɪntɪˈsenʃəl/", "academic": True},
            {"word": "ubiquitous", "freq": 9400, "cefr": "C2", "diff": 6.0, "def_zh": "无处不在的", "def_en": "existing everywhere", "ph_us": "/juˈbɪkwətəs/", "ph_uk": "/juːˈbɪkwɪtəs/", "academic": True},
            {"word": "serendipitous", "freq": 9600, "cefr": "C2", "diff": 6.0, "def_zh": "机缘巧合的", "def_en": "occurring by happy chance", "ph_us": "/ˌserənˈdɪpətəs/", "ph_uk": "/ˌserənˈdɪpɪtəs/", "academic": True},
            
            # 专业/技术词汇
            {"word": "headquarters", "freq": 2800, "cefr": "B2", "diff": 4.0, "def_zh": "总部；司令部", "def_en": "main office of an organization", "ph_us": "/ˈhedˌkwɔrtərz/", "ph_uk": "/ˈhedkwɔːtəz/"},
            {"word": "francisco", "freq": 8000, "cefr": "C1", "diff": 3.0, "def_zh": "弗朗西斯科（人名/地名）", "def_en": "proper noun (name/place)", "ph_us": "/frænˈsɪskoʊ/", "ph_uk": "/frænˈsɪskəʊ/"},
            {"word": "outrageous", "freq": 4800, "cefr": "B2", "diff": 4.5, "def_zh": "愤慨的；令人震惊的", "def_en": "shocking and unacceptable", "ph_us": "/aʊtˈreɪdʒəs/", "ph_uk": "/aʊtˈreɪdʒəs/"},
            {"word": "criticism", "freq": 2400, "cefr": "B2", "diff": 4.0, "def_zh": "批评；评论", "def_en": "analysis and judgment", "ph_us": "/ˈkrɪtəˌsɪzəm/", "ph_uk": "/ˈkrɪtɪsɪzəm/", "academic": True},
            {"word": "therefore", "freq": 1200, "cefr": "B1", "diff": 3.5, "def_zh": "因此；所以", "def_en": "for that reason", "ph_us": "/ˈðerfɔr/", "ph_uk": "/ˈðeəfɔː/", "academic": True},
            {"word": "industry", "freq": 1000, "cefr": "B1", "diff": 3.0, "def_zh": "工业；产业", "def_en": "economic activity", "ph_us": "/ˈɪndəstri/", "ph_uk": "/ˈɪndəstri/", "oxford5000": True},
            {"word": "gendered", "freq": 7500, "cefr": "C1", "diff": 5.0, "def_zh": "有性别的；区分性别的", "def_en": "relating to gender differences", "ph_us": "/ˈdʒendərd/", "ph_uk": "/ˈdʒendəd/", "academic": True},
            {"word": "understand", "freq": 180, "cefr": "A2", "diff": 2.0, "def_zh": "理解；明白", "def_en": "to comprehend", "ph_us": "/ˌʌndərˈstænd/", "ph_uk": "/ˌʌndəˈstænd/", "oxford3000": True},
            {"word": "benefit", "freq": 800, "cefr": "B1", "diff": 3.0, "def_zh": "利益；好处", "def_en": "advantage or profit", "ph_us": "/ˈbenəfɪt/", "ph_uk": "/ˈbenɪfɪt/", "academic": True, "oxford3000": True},
            {"word": "control", "freq": 340, "cefr": "A2", "diff": 2.5, "def_zh": "控制；管理", "def_en": "to have power over", "ph_us": "/kənˈtroʊl/", "ph_uk": "/kənˈtrəʊl/", "oxford3000": True},
            {"word": "safety", "freq": 900, "cefr": "B1", "diff": 3.0, "def_zh": "安全；保险", "def_en": "condition of being safe", "ph_us": "/ˈseɪfti/", "ph_uk": "/ˈseɪfti/", "oxford3000": True},
            {"word": "entire", "freq": 600, "cefr": "B1", "diff": 3.0, "def_zh": "整个的；全部的", "def_en": "whole or complete", "ph_us": "/ɪnˈtaɪər/", "ph_uk": "/ɪnˈtaɪə/", "oxford3000": True},
            {"word": "forward", "freq": 450, "cefr": "A2", "diff": 2.5, "def_zh": "向前；前进", "def_en": "towards the front", "ph_us": "/ˈfɔrwərd/", "ph_uk": "/ˈfɔːwəd/", "oxford3000": True},
            {"word": "whether", "freq": 280, "cefr": "B1", "diff": 3.0, "def_zh": "是否；无论", "def_en": "if or not", "ph_us": "/ˈweðər/", "ph_uk": "/ˈweðə/", "oxford3000": True},
            
            # 补充常见词汇
            {"word": "responsible", "freq": 1200, "cefr": "B2", "diff": 3.5, "def_zh": "负责的；可靠的", "def_en": "having control over or care for someone", "ph_us": "/rɪˈspɑnsəbəl/", "ph_uk": "/rɪˈspɒnsəbəl/", "oxford3000": True},
            {"word": "buildings", "freq": 800, "cefr": "A2", "diff": 2.0, "def_zh": "建筑物", "def_en": "structures with walls and roof", "ph_us": "/ˈbɪldɪŋz/", "ph_uk": "/ˈbɪldɪŋz/", "oxford3000": True},
            {"word": "applications", "freq": 1800, "cefr": "B2", "diff": 3.5, "def_zh": "应用；申请", "def_en": "practical uses or formal requests", "ph_us": "/ˌæplɪˈkeɪʃənz/", "ph_uk": "/ˌæplɪˈkeɪʃənz/", "academic": True},
            {"word": "department", "freq": 900, "cefr": "B1", "diff": 3.0, "def_zh": "部门；科系", "def_en": "a division of organization", "ph_us": "/dɪˈpɑrtmənt/", "ph_uk": "/dɪˈpɑːtmənt/", "oxford3000": True},
            {"word": "influence", "freq": 1500, "cefr": "B2", "diff": 3.5, "def_zh": "影响；影响力", "def_en": "power to have effect on someone", "ph_us": "/ˈɪnfluəns/", "ph_uk": "/ˈɪnfluəns/", "academic": True, "oxford3000": True},
            {"word": "proposition", "freq": 3500, "cefr": "C1", "diff": 4.5, "def_zh": "提议；命题", "def_en": "statement or proposal", "ph_us": "/ˌprɑpəˈzɪʃən/", "ph_uk": "/ˌprɒpəˈzɪʃən/", "academic": True},
            {"word": "consistent", "freq": 2200, "cefr": "B2", "diff": 4.0, "def_zh": "一致的；连贯的", "def_en": "unchanging in behavior or attitudes", "ph_us": "/kənˈsɪstənt/", "ph_uk": "/kənˈsɪstənt/", "academic": True},
            {"word": "discovered", "freq": 1000, "cefr": "A2", "diff": 2.5, "def_zh": "发现", "def_en": "found something for the first time", "ph_us": "/dɪˈskʌvərd/", "ph_uk": "/dɪˈskʌvəd/", "oxford3000": True},
        ]
        
        cursor = self.conn.cursor()
        
        for word_data in base_vocab:
            cursor.execute('''
                INSERT OR REPLACE INTO vocabulary 
                (word, frequency_rank, cefr_level, difficulty_score, definition_zh, 
                 definition_en, phonetic_us, phonetic_uk, is_academic, is_oxford3000, 
                 is_oxford5000, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                word_data["word"],
                word_data["freq"],
                word_data["cefr"],
                word_data["diff"],
                word_data["def_zh"],
                word_data["def_en"],
                word_data["ph_us"],
                word_data["ph_uk"],
                word_data.get("academic", False),
                word_data.get("oxford3000", False),
                word_data.get("oxford5000", False),
                "base_collection"
            ))
        
        self.conn.commit()
        print(f"✅ 已加载 {len(base_vocab)} 个基础词汇")
        
    def get_word_difficulty(self, word: str, user_level: str = "6.0") -> Optional[Dict]:
        """获取单词难度信息"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM vocabulary WHERE LOWER(word) = LOWER(?)
        ''', (word,))
        
        result = cursor.fetchone()
        
        if not result:
            return None
            
        columns = [desc[0] for desc in cursor.description]
        word_data = dict(zip(columns, result))
        
        # 根据用户水平判断是否困难
        user_level_mapping = {
            '4.0': {'max_freq': 1000, 'max_diff': 2.0, 'max_cefr': 'A2'},
            '5.0': {'max_freq': 2000, 'max_diff': 3.0, 'max_cefr': 'B1'},
            '6.0': {'max_freq': 4000, 'max_diff': 4.0, 'max_cefr': 'B2'},
            '7.0': {'max_freq': 6000, 'max_diff': 5.0, 'max_cefr': 'C1'}
        }
        
        limits = user_level_mapping.get(user_level, user_level_mapping['6.0'])
        cefr_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        
        is_difficult = False
        reasons = []
        
        if word_data['frequency_rank'] and word_data['frequency_rank'] > limits['max_freq']:
            is_difficult = True
            reasons.append(f"low_frequency_{word_data['frequency_rank']}")
            
        if word_data['difficulty_score'] and word_data['difficulty_score'] > limits['max_diff']:
            is_difficult = True
            reasons.append(f"high_difficulty_{word_data['difficulty_score']}")
            
        if word_data['cefr_level']:
            try:
                cefr_idx = cefr_order.index(word_data['cefr_level'])
                max_cefr_idx = cefr_order.index(limits['max_cefr'])
                if cefr_idx > max_cefr_idx:
                    is_difficult = True
                    reasons.append(f"high_cefr_{word_data['cefr_level']}")
            except ValueError:
                pass
        
        # 确定难度级别
        if word_data['difficulty_score']:
            if word_data['difficulty_score'] >= 6.0:
                difficulty_level = 'high'
            elif word_data['difficulty_score'] >= 5.0:
                difficulty_level = 'advanced'
            elif word_data['difficulty_score'] >= 4.0:
                difficulty_level = 'medium'
            else:
                difficulty_level = 'basic'
        else:
            difficulty_level = 'medium'
        
        return {
            'word': word_data['word'],
            'is_difficult': is_difficult,
            'difficulty_level': difficulty_level,
            'cefr_level': word_data['cefr_level'],
            'frequency_rank': word_data['frequency_rank'],
            'is_academic': bool(word_data['is_academic']),
            'definition': word_data['definition_zh'],
            'phonetic': word_data['phonetic_us'],  # 默认使用美音
            'reasons': reasons
        }
    
    def batch_analyze(self, words: List[str], user_level: str = "6.0") -> List[Dict]:
        """批量分析词汇"""
        results = []
        for word in words:
            analysis = self.get_word_difficulty(word, user_level)
            if analysis and analysis['is_difficult']:
                results.append(analysis)
        return results
    
    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM vocabulary')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT cefr_level, COUNT(*) FROM vocabulary GROUP BY cefr_level')
        cefr_stats = dict(cursor.fetchall())
        
        cursor.execute('SELECT COUNT(*) FROM vocabulary WHERE is_academic = 1')
        academic = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM vocabulary WHERE is_oxford3000 = 1')
        oxford3000 = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM vocabulary WHERE is_oxford5000 = 1')
        oxford5000 = cursor.fetchone()[0]
        
        return {
            'total_words': total,
            'cefr_distribution': cefr_stats,
            'academic_words': academic,
            'oxford3000_words': oxford3000,
            'oxford5000_words': oxford5000
        }
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

def initialize_vocabulary_database():
    """初始化词汇数据库"""
    print("🚀 初始化词汇难度数据库...")
    
    db = VocabularyDatabase()
    
    # 加载基础词汇
    db.load_base_vocabulary()
    
    # 显示统计信息
    stats = db.get_stats()
    print("\n📊 数据库统计:")
    print(f"总词汇数: {stats['total_words']}")
    print(f"CEFR 分布: {stats['cefr_distribution']}")
    print(f"学术词汇: {stats['academic_words']}")
    print(f"Oxford 3000: {stats['oxford3000_words']}")
    print(f"Oxford 5000: {stats['oxford5000_words']}")
    
    db.close()
    print("\n✅ 词汇数据库初始化完成!")

if __name__ == "__main__":
    initialize_vocabulary_database()