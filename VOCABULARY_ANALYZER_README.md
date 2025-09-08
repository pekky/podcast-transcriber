# 🎓 Enhanced Vocabulary & Sentence Analyzer - 增强词汇句子分析工具

自动从音频转录文件中提取和分析适合特定英语水平的词汇和复杂句子，生成详细的学习指南。

## ✨ 功能特点

### 📚 词汇分析
- 🔍 **智能词汇提取**: 从转录文件中识别适合学习的词汇
- 📊 **难度评估**: 基于词汇长度和复杂性评估难度级别
- 🔤 **音标发音**: 自动生成IPA音标发音
- 📚 **词根词缀分析**: 分析词汇的词根、前缀和后缀
- 📝 **例句生成**: 为每个词汇生成实用例句
- 🎯 **优先级分组**: 按重要性将词汇分为高、中、低优先级

### 📝 句子分析 🆕
- 🎯 **复杂句识别**: 自动识别超出阅读水平的难句
- 📏 **句长分析**: 分析句子长度和结构复杂度
- 🔍 **语法结构识别**: 识别被动语态、从句、分词等复杂语法
- ⚖️ **难度评级**: 按Basic/Intermediate/Advanced/Expert分级
- 💡 **理解指导**: 提供句子理解要点和学习建议
- ✏️ **简化对照**: 提供简化版本帮助理解

## 📦 安装依赖

```bash
pip3 install -r requirements_vocabulary.txt
```

或者手动安装：

```bash
pip3 install nltk requests
```

## 🚀 使用方法

### 基本用法

```bash
python3 vocabulary_analyzer.py "path/to/transcript.txt"
```

### 高级选项

```bash
# 指定输出目录
python3 vocabulary_analyzer.py "transcript.txt" -o output_directory/

# 设置英语水平（默认: 6.0-6.5）
python3 vocabulary_analyzer.py "transcript.txt" -l "7.0-7.5"

# 限制词汇数量（默认: 40）
python3 vocabulary_analyzer.py "transcript.txt" -m 20

# 完整示例
python3 vocabulary_analyzer.py "downloads/audio_transcript.txt" -o study_guides/ -l "6.0-6.5" -m 30
```

### 与音频转录工具集成使用

1. **首先转录音频**:
   ```bash
   # 交互式选择音频文件进行转录
   ./transcribe.sh
   
   # 或直接指定文件
   ./transcribe.sh "downloads/audio.mp3"
   ```

2. **然后分析词汇**:
   ```bash
   # 分析生成的转录文件
   python3 vocabulary_analyzer.py "downloads/audio_speakers.txt"
   ```

## 📋 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入的转录文件路径 | 必需 |
| `-o, --output` | 输出目录 | 与输入文件同目录 |
| `-l, --level` | 目标英语水平 | 6.0-6.5 |
| `-m, --max-words` | 最大词汇数量 | 40 |

## 📊 支持的英语水平

- **6.0-6.5**: 雅思中级水平（推荐）
- **7.0-7.5**: 雅思高级水平
- **5.5-6.0**: 雅思初中级水平

## 📁 输出文件格式

生成的学习指南包含：

### 📚 词汇分析部分
1. **词汇列表**: 每个词汇的详细信息
   - 国际音标发音
   - 词根词缀分析
   - 词性标注
   - 定义解释
   - 同根词
   - 实用例句

2. **优先级分组**: 
   - 🔴 高优先级（务必掌握）
   - 🟡 中优先级（建议掌握）
   - 🟢 低优先级（了解即可）

### 📝 句子分析部分 🆕
3. **复杂句子分析**: 最多10个最难的句子
   - 📊 **复杂度分析**: 句子长度、难度评分、复杂因素
   - 🔍 **语法结构**: 被动语态、从句、分词等结构识别
   - 💡 **理解要点**: 针对性的理解指导
   - ✏️ **简化对照**: 简化版本帮助理解核心意思

4. **学习建议**: 
   - 词汇学习策略
   - 句子理解技巧
   - 具体的学习方法和步骤

## 🎯 使用示例

### 完整工作流程

```bash
# 1. 下载音频（可选）
python3 podcast_downloader.py

# 2. 转录音频
./transcribe.sh

# 3. 分析词汇
python3 vocabulary_analyzer.py "downloads/transcript_speakers.txt" -m 25

# 4. 查看生成的学习指南
ls downloads/*Vocabulary_Study.txt
```

### 批量处理

```bash
# 处理downloads目录下的所有转录文件
for file in downloads/*_speakers.txt; do
    python3 vocabulary_analyzer.py "$file" -m 20
done
```

## 🔧 自定义配置

可以通过修改 `VocabularyAnalyzer` 类来自定义：

- 词汇难度评估标准
- 词根词缀数据库
- 例句生成模板
- 优先级分组逻辑

## 🚨 注意事项

1. **首次运行**: 会自动下载NLTK数据包，请确保网络连接正常
2. **文件格式**: 支持UTF-8编码的.txt转录文件
3. **处理时间**: 长文本分析需要几分钟时间
4. **内存使用**: 大文件可能需要较多内存

## 🎓 学习建议

1. **结合音频**: 边听原音频边学习词汇，效果最佳
2. **分批学习**: 先掌握高优先级词汇，再学习其他
3. **定期复习**: 使用生成的例句进行练习
4. **实际应用**: 尝试在写作中使用这些高级词汇

## 🔄 更新日志

- v1.0: 基础词汇分析功能
- 支持多种英语水平设定
- 自动音标生成
- 词根词缀分析

## 🤝 贡献

欢迎提交改进建议和功能请求！

---

**💡 提示**: 这个工具特别适合准备雅思考试、托福考试或者想要提高英语词汇量的学习者使用。