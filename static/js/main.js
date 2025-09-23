// Podcast Transcriber Web App JavaScript

class PodcastTranscriber {
    constructor() {
        this.currentDownloadTask = null;
        this.currentTranscribeTask = null;
        this.audioFile = null;
        this.hasExistingTranscript = false;
        this.existingTranscriptData = null;
        this.forceRetranscribeConfirmed = false;
        this.englishLevel = this.getStoredEnglishLevel(); // 从cookie读取英语水平
        this.accentPreference = this.getStoredAccentPreference(); // 从cookie读取发音偏好
        this.audioCache = new Map(); // 音频缓存
        this.definitionCache = new Map(); // 详细释义缓存
        this.currentTranscriptContent = ''; // 当前转录内容
        
        this.initializeElements();
        this.bindEvents();
        this.showToast = this.showToast.bind(this);
        
        // 初始化词库
        this.vocabularyDatabase = null;
        this.loadVocabularyDatabase();
        
        // 初始加载音频文件列表
        this.loadAudioFiles();
    }
    
    initializeElements() {
        // Header控制元素
        this.addAudioBtn = document.getElementById('addAudioBtn');
        
        // 下载相关元素
        this.urlInput = document.getElementById('urlInput');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.downloadProgress = document.getElementById('downloadProgress');
        this.downloadStatus = document.getElementById('downloadStatus');
        this.downloadResult = document.getElementById('downloadResult');
        this.audioFileName = document.getElementById('audioFileName');
        this.downloadLink = document.getElementById('downloadLink');
        
        // 转录相关元素
        this.audioSelector = document.getElementById('audioSelector');
        this.withSpeakers = document.getElementById('withSpeakers');
        this.outputFormat = document.getElementById('outputFormat');
        this.transcribeBtn = document.getElementById('transcribeBtn');
        this.transcribeProgress = document.getElementById('transcribeProgress');
        this.transcribeStatus = document.getElementById('transcribeStatus');
        this.transcribeActions = document.getElementById('transcribeActions');
        
        // 结果显示元素
        this.emptyState = document.getElementById('emptyState');
        this.transcriptContent = document.getElementById('transcriptContent');
        this.transcriptText = document.getElementById('transcriptText');
        this.transcriptMeta = document.getElementById('transcriptMeta');
        this.transcriptTime = document.getElementById('transcriptTime');
        
        // 操作按钮
        this.exportBtn = document.getElementById('exportBtn');
        this.clearBtn = document.getElementById('clearBtn');
        
        // 英语学习面板元素
        this.vocabEmptyState = document.getElementById('vocabEmptyState');
        this.vocabContent = document.getElementById('vocabContent');
        this.vocabProgress = document.getElementById('vocabProgress');
        this.vocabList = document.getElementById('vocabList');
        this.sentenceList = document.getElementById('sentenceList');
        this.vocabCount = document.getElementById('vocabCount');
        this.sentenceCount = document.getElementById('sentenceCount');
        
        // 模态框
        this.downloadModal = new bootstrap.Modal(document.getElementById('downloadModal'));
        
        // Toast 元素
        this.successToast = new bootstrap.Toast(document.getElementById('successToast'));
        this.errorToast = new bootstrap.Toast(document.getElementById('errorToast'));
    }
    
    bindEvents() {
        // 添加音频按钮点击 - 显示下载模态框
        this.addAudioBtn.addEventListener('click', () => {
            this.downloadModal.show();
        });
        
        // URL 输入变化
        this.urlInput.addEventListener('input', () => {
            const hasUrl = this.urlInput.value.trim().length > 0;
            this.downloadBtn.disabled = !hasUrl;
            
            if (hasUrl) {
                this.downloadBtn.innerHTML = '<i class="fas fa-download me-1"></i>开始下载';
            }
        });
        
        // 下载按钮点击
        this.downloadBtn.addEventListener('click', () => {
            this.startDownload();
        });
        
        // 音频选择器变化
        this.audioSelector.addEventListener('change', () => {
            this.updateTranscribeButtonState();
            this.checkExistingTranscript();
        });
        
        // 转录按钮点击
        this.transcribeBtn.addEventListener('click', () => {
            this.startTranscribe();
        });
        
        // 导出按钮点击
        this.exportBtn.addEventListener('click', () => {
            this.exportMarkdown();
        });
        
        // 清空按钮点击
        this.clearBtn.addEventListener('click', () => {
            this.clearResults();
        });
        
        // 回车键支持
        this.urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.downloadBtn.disabled) {
                this.startDownload();
            }
        });
        
        // 确认重新转录按钮
        document.getElementById('confirmRetranscribe').addEventListener('click', () => {
            this.forceRetranscribe();
        });
        
        // 英语水平选择
        document.querySelectorAll('[data-level]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.setEnglishLevel(e.target.dataset.level);
            });
        });
        
        // 发音偏好选择
        document.querySelectorAll('[data-accent]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.setAccentPreference(e.target.dataset.accent);
            });
        });
        
        // 初始化发音偏好显示和英语水平显示
        this.updateAccentUI();
        this.updateEnglishLevelUI();
    }
    
    async loadAudioFiles() {
        try {
            const response = await fetch('/api/audio-files');
            const data = await response.json();
            
            if (data.success) {
                this.populateAudioSelector(data.files);
            } else {
                console.error('Error loading audio files:', data.error);
                this.audioSelector.innerHTML = '<option value="">无法加载音频文件</option>';
            }
        } catch (error) {
            console.error('Error loading audio files:', error);
            this.audioSelector.innerHTML = '<option value="">网络错误，无法加载音频文件</option>';
        }
    }
    
    // 加载词库数据库
    async loadVocabularyDatabase() {
        try {
            console.log('📚 开始加载词库数据...');
            
            // 加载50k词频表
            const response = await fetch('/static/english-50k-frequency.txt');
            const text = await response.text();
            
            // 解析词频数据
            const vocabularyMap = new Map();
            const lines = text.trim().split('\n');
            
            lines.forEach((line, index) => {
                const parts = line.trim().split(' ');
                if (parts.length >= 2) {
                    const word = parts[0].toLowerCase();
                    const frequency = parseInt(parts[1]);
                    
                    // 过滤掉非字母单词和太短的单词
                    if (/^[a-z]+$/.test(word) && word.length > 2) {
                        // 基于频率排名计算难度级别
                        let difficultyLevel;
                        let cefrLevel;
                        
                        if (index < 1000) {
                            difficultyLevel = 'easy';
                            cefrLevel = 'A1';
                        } else if (index < 3000) {
                            difficultyLevel = 'easy';
                            cefrLevel = 'A2';
                        } else if (index < 5000) {
                            difficultyLevel = 'medium';
                            cefrLevel = 'B1';
                        } else if (index < 10000) {
                            difficultyLevel = 'medium';
                            cefrLevel = 'B2';
                        } else if (index < 20000) {
                            difficultyLevel = 'advanced';
                            cefrLevel = 'C1';
                        } else {
                            difficultyLevel = 'high';
                            cefrLevel = 'C2';
                        }
                        
                        vocabularyMap.set(word, {
                            word: word,
                            frequency: frequency,
                            rank: index + 1,
                            difficulty: difficultyLevel,
                            cefr: cefrLevel,
                            phonetic: `/ˈ${word}/`, // 简化音标
                            definition: `${word}的释义` // 占位符定义
                        });
                    }
                }
            });
            
            this.vocabularyDatabase = vocabularyMap;
            console.log(`✅ 词库加载完成！包含 ${vocabularyMap.size} 个单词`);
            
        } catch (error) {
            console.error('❌ 词库加载失败:', error);
            console.log('🔄 使用内置小词库作为备选');
            // 如果加载失败，使用现有的小词库
            this.vocabularyDatabase = null;
        }
    }
    
    populateAudioSelector(files) {
        this.audioSelector.innerHTML = '';
        
        if (files.length === 0) {
            this.audioSelector.innerHTML = '<option value="">暂无已下载的音频文件</option>';
            return;
        }
        
        // 添加默认选项
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '请选择音频文件...';
        this.audioSelector.appendChild(defaultOption);
        
        // 添加音频文件选项
        files.forEach(file => {
            const option = document.createElement('option');
            option.value = file.filename;
            option.textContent = `${file.filename} (${file.size_mb} MB, ${file.modified})`;
            this.audioSelector.appendChild(option);
        });
        
        this.updateTranscribeButtonState();
    }
    
    updateTranscribeButtonState() {
        // 检查是否有选择的音频文件或已下载的文件
        const hasSelectedFile = this.audioSelector.value !== '';
        const hasDownloadedFile = this.audioFile !== null;
        
        this.transcribeBtn.disabled = !(hasSelectedFile || hasDownloadedFile);
    }
    
    async checkExistingTranscript() {
        const selectedFile = this.audioSelector.value;
        
        console.log('Checking existing transcript for:', selectedFile);
        
        if (!selectedFile) {
            // 如果没有选择文件，清空转录结果显示
            this.clearTranscriptDisplay();
            return;
        }
        
        try {
            const url = `/api/transcript/${encodeURIComponent(selectedFile)}`;
            console.log('Fetching transcript from:', url);
            
            const response = await fetch(url);
            const data = await response.json();
            
            console.log('Transcript API response:', data);
            
            if (data.success && data.exists) {
                // 显示现有转录结果
                console.log('Found existing transcript, displaying...');
                this.displayExistingTranscript(data.transcript, data.created);
                // 标记此文件已转录
                this.hasExistingTranscript = true;
                this.existingTranscriptData = data;
            } else {
                // 清空显示
                console.log('No existing transcript found');
                this.clearTranscriptDisplay();
                this.hasExistingTranscript = false;
                this.existingTranscriptData = null;
            }
        } catch (error) {
            console.error('Error checking existing transcript:', error);
            this.clearTranscriptDisplay();
            this.hasExistingTranscript = false;
            this.existingTranscriptData = null;
        }
    }
    
    displayExistingTranscript(transcript, created) {
        // 检测内容变化
        const hasContentChanged = this.detectTranscriptChange(transcript);
        
        // 显示转录内容
        this.emptyState.classList.add('d-none');
        this.transcriptContent.classList.remove('d-none');
        this.transcriptText.innerHTML = this.formatTranscript(transcript);
        
        // 显示元数据
        this.transcriptMeta.classList.remove('d-none');
        this.transcriptTime.textContent = `转录时间: ${created}`;
        
        // 显示操作按钮
        this.transcribeActions.classList.remove('d-none');
        
        // 如果内容有变化，自动分析词汇
        if (hasContentChanged) {
            this.analyzeVocabulary(transcript);
        }
    }
    
    clearTranscriptDisplay() {
        this.emptyState.classList.remove('d-none');
        this.transcriptContent.classList.add('d-none');
        this.transcriptMeta.classList.add('d-none');
        this.transcribeActions.classList.add('d-none');
    }
    
    async startDownload() {
        const url = this.urlInput.value.trim();
        
        if (!url) {
            this.showToast('error', '请输入有效的 URL');
            return;
        }
        
        // 验证 URL 格式
        if (!this.isValidUrl(url)) {
            this.showToast('error', '请输入有效的 Podcast 或 YouTube 链接');
            return;
        }
        
        try {
            // UI 状态更新
            this.downloadBtn.disabled = true;
            this.downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.downloadProgress.classList.remove('d-none');
            this.downloadResult.classList.add('d-none');
            this.updateProgressBar(this.downloadProgress, 0);
            this.downloadStatus.textContent = '准备下载...';
            
            // 发送下载请求
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || '下载请求失败');
            }
            
            // 开始轮询任务状态
            this.currentDownloadTask = result.task_id;
            this.pollDownloadStatus();
            
        } catch (error) {
            console.error('Download error:', error);
            this.showToast('error', `下载失败: ${error.message}`);
            this.resetDownloadUI();
        }
    }
    
    async pollDownloadStatus() {
        if (!this.currentDownloadTask) return;
        
        try {
            const response = await fetch(`/api/status/${this.currentDownloadTask}`);
            const data = await response.json();
            const status = data.status;
            
            // 更新状态显示
            this.downloadStatus.innerHTML = `
                <span class="status-indicator ${status.status}"></span>
                ${status.message || '处理中...'}
            `;
            
            // 更新进度条
            this.updateProgressBar(this.downloadProgress, status.progress || 0);
            
            if (status.status === 'completed' && data.result) {
                // 下载完成
                this.handleDownloadComplete(data.result);
            } else if (status.status === 'error') {
                // 下载失败
                throw new Error(status.message || '下载失败');
            } else if (status.status !== 'completed') {
                // 继续轮询
                setTimeout(() => this.pollDownloadStatus(), 2000);
            }
            
        } catch (error) {
            console.error('Status polling error:', error);
            this.showToast('error', `状态查询失败: ${error.message}`);
            this.resetDownloadUI();
        }
    }
    
    handleDownloadComplete(result) {
        if (result.success) {
            // 存储音频文件信息
            this.audioFile = result.audio_file;
            
            // 更新 UI
            this.downloadProgress.classList.add('d-none');
            this.downloadResult.classList.remove('d-none');
            this.audioFileName.textContent = result.filename;
            this.downloadLink.href = result.download_url;
            
            // 启用转录按钮
            this.transcribeBtn.disabled = false;
            
            // 重新加载音频文件列表
            this.loadAudioFiles();
            
            // 自动选择刚下载的文件
            setTimeout(() => {
                const option = Array.from(this.audioSelector.options).find(opt => 
                    opt.textContent.includes(result.filename)
                );
                if (option) {
                    this.audioSelector.value = option.value;
                    this.updateTranscribeButtonState();
                    this.checkExistingTranscript();
                }
            }, 500);
            
            this.showToast('success', '音频下载完成！');
            
            // 自动关闭下载模态框
            setTimeout(() => {
                this.downloadModal.hide();
            }, 2000);
        } else {
            throw new Error(result.error || '下载失败');
        }
        
        this.resetDownloadUI();
    }
    
    resetDownloadUI() {
        this.downloadBtn.disabled = this.urlInput.value.trim().length === 0;
        this.downloadBtn.innerHTML = '<i class="fas fa-download me-1"></i>开始下载';
        this.currentDownloadTask = null;
    }
    
    async startTranscribe() {
        const selectedFile = this.audioSelector.value;
        
        if (!selectedFile && !this.audioFile) {
            this.showToast('error', '请选择音频文件或先下载音频');
            return;
        }
        
        // 如果选择的文件已有转录且用户未确认强制转录，显示确认对话框
        if (selectedFile && this.hasExistingTranscript && !this.forceRetranscribeConfirmed) {
            this.showRetranscribeConfirmation(selectedFile);
            return;
        }
        
        try {
            // UI 状态更新
            this.transcribeBtn.disabled = true;
            this.transcribeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 转录中...';
            this.transcribeProgress.classList.remove('d-none');
            this.transcribeActions.classList.add('d-none');
            this.updateProgressBar(this.transcribeProgress, 0, 'bg-success');
            this.transcribeStatus.textContent = '准备转录...';
            
            // 准备请求数据
            const requestData = {
                with_speakers: this.withSpeakers.checked,
                output_format: this.outputFormat.value,
                force_retranscribe: this.forceRetranscribeConfirmed || false
            };
            
            // 优先使用选择的文件
            if (selectedFile) {
                requestData.selected_file = selectedFile;
            } else {
                requestData.audio_file = this.audioFile;
            }
            
            // 重置强制转录标志
            this.forceRetranscribeConfirmed = false;
            
            // 发送转录请求
            const response = await fetch('/api/transcribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || '转录请求失败');
            }
            
            // 开始轮询任务状态
            this.currentTranscribeTask = result.task_id;
            this.pollTranscribeStatus();
            
        } catch (error) {
            console.error('Transcribe error:', error);
            this.showToast('error', `转录失败: ${error.message}`);
            this.resetTranscribeUI();
        }
    }
    
    async pollTranscribeStatus() {
        if (!this.currentTranscribeTask) return;
        
        try {
            const response = await fetch(`/api/status/${this.currentTranscribeTask}`);
            const data = await response.json();
            const status = data.status;
            
            // 更新状态显示
            this.transcribeStatus.innerHTML = `
                <span class="status-indicator ${status.status}"></span>
                ${status.message || '转录中...'}
            `;
            
            // 更新进度条
            this.updateProgressBar(this.transcribeProgress, status.progress || 0, 'bg-success');
            
            if (status.status === 'completed' && data.result) {
                // 转录完成
                this.handleTranscribeComplete(data.result);
            } else if (status.status === 'error') {
                // 转录失败
                throw new Error(status.message || '转录失败');
            } else if (status.status !== 'completed') {
                // 继续轮询
                setTimeout(() => this.pollTranscribeStatus(), 3000);
            }
            
        } catch (error) {
            console.error('Transcribe status polling error:', error);
            this.showToast('error', `转录状态查询失败: ${error.message}`);
            this.resetTranscribeUI();
        }
    }
    
    handleTranscribeComplete(result) {
        if (result.success) {
            // 显示转录结果
            this.displayTranscript(result.transcript);
            
            // 更新 UI
            this.transcribeProgress.classList.add('d-none');
            this.transcribeActions.classList.remove('d-none');
            
            // 更新元数据
            this.transcriptMeta.classList.remove('d-none');
            this.transcriptTime.textContent = new Date().toLocaleString('zh-CN');
            
            this.showToast('success', '转录完成！');
        } else {
            throw new Error(result.error || '转录失败');
        }
        
        this.resetTranscribeUI();
    }
    
    resetTranscribeUI() {
        this.transcribeBtn.disabled = false;
        this.transcribeBtn.innerHTML = '<i class="fas fa-play me-1"></i>开始转录';
        this.currentTranscribeTask = null;
    }
    
    showRetranscribeConfirmation(filename) {
        // 填充对话框信息
        document.getElementById('existingTranscriptTime').textContent = this.existingTranscriptData.created;
        document.getElementById('existingAudioFile').textContent = filename;
        
        // 显示对话框
        const modal = new bootstrap.Modal(document.getElementById('retranscribeModal'));
        modal.show();
    }
    
    forceRetranscribe() {
        // 设置强制转录标志
        this.forceRetranscribeConfirmed = true;
        
        // 关闭对话框
        const modal = bootstrap.Modal.getInstance(document.getElementById('retranscribeModal'));
        modal.hide();
        
        // 开始转录
        this.startTranscribe();
    }
    
    displayTranscript(text) {
        // 隐藏空状态
        this.emptyState.classList.add('d-none');
        this.transcriptContent.classList.remove('d-none');
        
        // 检测内容变化并自动刷新词汇分析
        const hasContentChanged = this.detectTranscriptChange(text);
        
        // 格式化转录文本
        const formattedText = this.formatTranscript(text);
        this.transcriptText.innerHTML = formattedText;
        
        // 添加动画效果
        this.transcriptContent.classList.add('fade-in');
        
        // 滚动到顶部
        this.transcriptText.scrollTop = 0;
        
        // 如果内容有变化或首次显示，进行词汇分析
        if (hasContentChanged || this.vocabEmptyState && !this.vocabEmptyState.classList.contains('d-none')) {
            this.analyzeVocabulary(text);
        }
    }
    
    formatTranscript(text) {
        // 检测是否包含说话人信息
        const hasSpeakers = /^[A-Z]:|→[A-Z]:/.test(text);
        
        if (hasSpeakers) {
            // 格式化带说话人的转录文本
            return text
                .split('\n')
                .map(line => {
                    line = line.trim();
                    if (!line) return '<br>';
                    
                    // 处理说话人标识
                    if (line.match(/^[A-Z]:|→[A-Z]:/)) {
                        const [speaker, ...content] = line.split(':');
                        const cleanSpeaker = speaker.replace('→', '').trim();
                        return `
                            <div class="speaker-label">
                                <i class="fas fa-user me-1"></i>Speaker ${cleanSpeaker}:
                            </div>
                            <div class="mb-3">${content.join(':').trim()}</div>
                        `;
                    } else {
                        return `<div class="mb-2">${line}</div>`;
                    }
                })
                .join('');
        } else {
            // 普通文本格式化
            return text
                .split('\n')
                .map(line => {
                    line = line.trim();
                    if (!line) return '<br>';
                    return `<p class="mb-2">${line}</p>`;
                })
                .join('');
        }
    }
    
    async exportMarkdown() {
        if (!this.currentTranscribeTask) {
            this.showToast('error', '没有可导出的转录结果');
            return;
        }
        
        try {
            const link = document.createElement('a');
            link.href = `/api/export/${this.currentTranscribeTask}`;
            link.download = `transcript_${Date.now()}.md`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showToast('success', 'Markdown 文件导出成功！');
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('error', '导出失败');
        }
    }
    
    clearResults() {
        // 重置所有状态
        this.audioFile = null;
        this.currentDownloadTask = null;
        this.currentTranscribeTask = null;
        
        // 重置 UI
        this.urlInput.value = '';
        this.downloadBtn.disabled = true;
        this.transcribeBtn.disabled = true;
        this.withSpeakers.checked = false;
        
        // 隐藏所有进度和结果
        this.downloadProgress.classList.add('d-none');
        this.downloadResult.classList.add('d-none');
        this.transcribeProgress.classList.add('d-none');
        this.transcribeActions.classList.add('d-none');
        this.transcriptContent.classList.add('d-none');
        this.transcriptMeta.classList.add('d-none');
        
        // 重置词汇学习面板
        this.vocabContent.classList.add('d-none');
        this.vocabProgress.classList.add('d-none');
        this.vocabEmptyState.classList.remove('d-none');
        
        // 显示空状态
        this.emptyState.classList.remove('d-none');
        
        // 重置按钮状态
        this.resetDownloadUI();
        this.resetTranscribeUI();
        
        this.showToast('success', '已清空所有结果');
    }
    
    updateProgressBar(container, progress, bgClass = 'bg-primary') {
        const progressBar = container.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${Math.max(progress, 5)}%`;
            progressBar.className = `progress-bar ${bgClass}`;
        }
    }
    
    isValidUrl(url) {
        // 检查是否是有效的 URL
        try {
            new URL(url);
            
            // 检查是否是支持的平台
            const supportedDomains = [
                'podcasts.apple.com',
                'youtube.com',
                'youtu.be',
                'soundcloud.com',
                'spotify.com'
            ];
            
            const urlObj = new URL(url);
            const isSupported = supportedDomains.some(domain => 
                urlObj.hostname.includes(domain)
            );
            
            // 如果不是已知域名，检查是否可能是 RSS 订阅
            const isRss = url.includes('rss') || url.includes('feed') || url.includes('.xml');
            
            return isSupported || isRss;
        } catch {
            return false;
        }
    }
    
    showToast(type, message) {
        const toast = type === 'success' ? this.successToast : this.errorToast;
        const toastBody = toast._element.querySelector('.toast-body');
        
        toastBody.textContent = message;
        toast.show();
    }
    
    // Cookie操作方法
    setCookie(name, value, days = 365) {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
    }
    
    getCookie(name) {
        return document.cookie.split('; ').reduce((r, v) => {
            const parts = v.split('=');
            return parts[0] === name ? decodeURIComponent(parts[1]) : r;
        }, '');
    }
    
    // 获取存储的英语水平
    getStoredEnglishLevel() {
        const stored = this.getCookie('englishLevel');
        // 默认返回"中高级"(IELTS 6.0)
        return stored || '6.0';
    }
    
    // 获取存储的发音偏好
    getStoredAccentPreference() {
        const stored = this.getCookie('accentPreference');
        // 默认返回美音
        return stored || 'us';
    }
    
    // 检测转录内容变化
    detectTranscriptChange(newContent) {
        const normalizedNew = newContent.trim();
        const normalizedCurrent = this.currentTranscriptContent.trim();
        
        if (normalizedNew && normalizedNew !== normalizedCurrent) {
            this.currentTranscriptContent = normalizedNew;
            return true;
        }
        return false;
    }
    
    // 设置英语水平
    setEnglishLevel(level) {
        this.englishLevel = level;
        
        // 保存到cookie
        this.setCookie('englishLevel', level);
        
        // 更新UI显示
        document.querySelectorAll('[data-level]').forEach(item => {
            item.classList.toggle('active', item.dataset.level === level);
        });
        
        // 如果有转录内容，重新分析
        if (!this.transcriptContent.classList.contains('d-none')) {
            const transcriptText = this.transcriptText.textContent;
            if (transcriptText) {
                this.analyzeVocabulary(transcriptText);
            }
        }
    }
    
    // 词汇分析
    async analyzeVocabulary(text) {
        if (!text || text.trim().length === 0) return;
        
        try {
            // 显示分析进度
            this.vocabEmptyState.classList.add('d-none');
            this.vocabContent.classList.add('d-none');
            this.vocabProgress.classList.remove('d-none');
            
            // 模拟词汇分析过程（实际应该调用后端API）
            await this.simulateVocabAnalysis(text);
            
        } catch (error) {
            console.error('Vocabulary analysis error:', error);
            this.vocabProgress.classList.add('d-none');
            this.vocabEmptyState.classList.remove('d-none');
        }
    }
    
    // 词汇分析（使用前端本地大词库）
    async simulateVocabAnalysis(text) {
        const progressBar = this.vocabProgress.querySelector('.progress-bar');
        
        console.log(`🧪 开始前端词汇分析 - 用户水平: ${this.englishLevel}, 文本长度: ${text.length}`);
        progressBar.style.width = '20%';
        
        // 模拟分析过程
        const updateProgress = () => {
            const currentWidth = parseInt(progressBar.style.width) || 20;
            if (currentWidth < 90) {
                progressBar.style.width = `${currentWidth + Math.random() * 15}%`;
            }
        };
        
        const progressInterval = setInterval(updateProgress, 200);
        
        // 模拟分析时间
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        
        // 使用本地词汇分析
        const mockVocab = this.generateMockVocabulary(text);
        const mockSentences = this.generateMockSentences(text);
        
        console.log(`✅ 前端词汇分析完成 - 生词数: ${mockVocab.length}, 句子数: ${mockSentences.length}`);
        
        setTimeout(() => {
            this.displayVocabularyResults(mockVocab, mockSentences, false);
        }, 300);
    }
    
    // 生成基于转录内容的生词数据（使用大词库）
    generateMockVocabulary(text) {
        const words = text.toLowerCase().match(/\b[a-z]+\b/g) || [];
        const uniqueWords = [...new Set(words)].filter(word => word.length > 2);
        
        console.log(`🔍 分析 ${uniqueWords.length} 个独特单词，用户水平：${this.englishLevel}`);
        
        // 如果大词库不可用，使用备用词库
        if (!this.vocabularyDatabase) {
            return this.generateFallbackVocabulary(uniqueWords);
        }
        
        // 根据英语水平确定难度阈值
        const difficultyThresholds = {
            '4.0': { maxRank: 1000, showLevels: ['medium', 'advanced', 'high'] },    // 初级：1000词以外都算难
            '5.0': { maxRank: 3000, showLevels: ['medium', 'advanced', 'high'] },    // 中级：3000词以外算难
            '6.0': { maxRank: 8000, showLevels: ['advanced', 'high'] },              // 中高级：8000词以外算难
            '7.0': { maxRank: 15000, showLevels: ['high'] }                          // 高级：15000词以外算难
        };
        
        const threshold = difficultyThresholds[this.englishLevel] || difficultyThresholds['6.0'];
        
        // 分析文本中的困难词汇
        const difficultWords = [];
        uniqueWords.forEach(word => {
            const wordData = this.vocabularyDatabase.get(word);
            
            if (wordData) {
                // 基于频率排名判断难度
                if (wordData.rank > threshold.maxRank && threshold.showLevels.includes(wordData.difficulty)) {
                    difficultWords.push({
                        word: wordData.word,
                        phonetic: wordData.phonetic,
                        definition: this.getChineseDefinition(wordData.word),
                        level: wordData.difficulty,
                        cefr: wordData.cefr,
                        rank: wordData.rank,
                        frequency: wordData.frequency
                    });
                }
            } else if (word.length > 6) {
                // 对于词库中没有的长单词，推测为高难度
                difficultWords.push({
                    word: word,
                    phonetic: `/ˈ${word}/`,
                    definition: `${word}的释义（未知词汇）`,
                    level: word.length > 10 ? 'high' : 'advanced',
                    cefr: word.length > 10 ? 'C2' : 'C1',
                    rank: 50000,
                    frequency: 1
                });
            }
        });
        
        // 按难度和频率排序（更难的和更罕见的排在前面）
        difficultWords.sort((a, b) => {
            // 先按级别排序
            const levelOrder = { 'high': 3, 'advanced': 2, 'medium': 1 };
            const levelDiff = (levelOrder[b.level] || 0) - (levelOrder[a.level] || 0);
            if (levelDiff !== 0) return levelDiff;
            
            // 再按排名排序（排名越高越难）
            return b.rank - a.rank;
        });
        
        // 根据用户水平限制返回数量
        const maxWords = {
            '4.0': 20,  // 初级显示更多帮助学习
            '5.0': 15,  // 中级适中数量
            '6.0': 12,  // 中高级减少数量
            '7.0': 8    // 高级只显示最难的词汇
        };
        
        const limit = maxWords[this.englishLevel] || 12;
        const result = difficultWords.slice(0, Math.min(limit, difficultWords.length));
        
        console.log(`📊 从 ${uniqueWords.length} 个单词中识别出 ${result.length} 个困难词汇`);
        
        return result;
    }
    
    // 备用词库（当大词库加载失败时使用）
    generateFallbackVocabulary(uniqueWords) {
        console.log('🔄 使用备用小词库');
        
        // 简化的内置词库
        const miniDatabase = {
            'phenomenon': { phonetic: '/fɪˈnɒmɪnən/', definition: '现象；奇迹', level: 'high' },
            'sophisticated': { phonetic: '/səˈfɪstɪkeɪtɪd/', definition: '精密的；老练的', level: 'advanced' },
            'comprehensive': { phonetic: '/ˌkɒmprɪˈhensɪv/', definition: '综合的；全面的', level: 'medium' },
            'innovation': { phonetic: '/ˌɪnəˈveɪʃn/', definition: '创新；革新', level: 'medium' },
            'artificial': { phonetic: '/ˌɑːtɪˈfɪʃl/', definition: '人工的；人造的', level: 'medium' },
            'intelligence': { phonetic: '/ɪnˈtelɪdʒəns/', definition: '智力；智能', level: 'medium' },
            'technology': { phonetic: '/tekˈnɒlədʒi/', definition: '技术；科技', level: 'medium' },
            'responsibility': { phonetic: '/rɪˌspɒnsəˈbɪləti/', definition: '责任；职责', level: 'advanced' },
            'environment': { phonetic: '/ɪnˈvaɪrənmənt/', definition: '环境；周围', level: 'medium' },
            'significant': { phonetic: '/sɪɡˈnɪfɪkənt/', definition: '重要的；显著的', level: 'advanced' }
        };
        
        const foundWords = [];
        uniqueWords.forEach(word => {
            if (miniDatabase[word]) {
                foundWords.push({
                    word: word,
                    ...miniDatabase[word]
                });
            } else if (word.length > 7) {
                foundWords.push({
                    word: word,
                    phonetic: `/ˈ${word}/`,
                    definition: `${word}的释义`,
                    level: word.length > 10 ? 'high' : 'advanced'
                });
            }
        });
        
        return foundWords.slice(0, 8);
    }
    
    // 获取中文释义（可以扩展为查询在线词典）
    getChineseDefinition(word) {
        // 基础词汇的中文释义映射
        const basicDefinitions = {
            'phenomenon': '现象；奇迹',
            'sophisticated': '精密的；老练的',
            'comprehensive': '综合的；全面的',
            'innovation': '创新；革新',
            'sustainable': '可持续的',
            'artificial': '人工的；人造的',
            'intelligence': '智力；智能',
            'technology': '技术；科技',
            'responsibility': '责任；职责',
            'environment': '环境；周围',
            'significant': '重要的；显著的',
            'development': '发展；开发',
            'organization': '组织；机构',
            'information': '信息；资料',
            'government': '政府；管理',
            'opportunity': '机会；时机',
            'education': '教育；培养',
            'experience': '经验；体验',
            'available': '可用的；有效的',
            'important': '重要的；主要的',
            'different': '不同的；各种的'
        };
        
        return basicDefinitions[word] || `${word}的释义`;
    }
    
    // 生成基于转录内容的复杂句子
    generateMockSentences(text) {
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 20);
        
        // 分析句子复杂度的关键词
        const complexityIndicators = {
            high: ['therefore', 'however', 'nevertheless', 'consequently', 'furthermore', 'moreover', 'whereas', 'albeit', 'notwithstanding'],
            advanced: ['although', 'because', 'since', 'unless', 'whether', 'while', 'despite', 'regarding', 'concerning'],
            medium: ['when', 'where', 'which', 'that', 'who', 'what', 'how', 'why', 'if', 'as']
        };
        
        const complexSentences = [];
        
        sentences.forEach(sentence => {
            const cleanSentence = sentence.trim();
            if (cleanSentence.length < 30) return; // 过滤太短的句子
            
            const words = cleanSentence.toLowerCase().split(/\s+/);
            let complexityLevel = 'Simple';
            let complexityReason = '';
            
            // 检查复杂度指标
            for (const [level, indicators] of Object.entries(complexityIndicators)) {
                if (indicators.some(indicator => words.includes(indicator))) {
                    if (level === 'high') {
                        complexityLevel = 'Highly Complex';
                        complexityReason = '包含高级连接词';
                        break;
                    } else if (level === 'advanced') {
                        complexityLevel = 'Advanced';
                        complexityReason = '包含从属连词';
                        break;
                    } else if (level === 'medium') {
                        complexityLevel = 'Complex Structure';
                        complexityReason = '包含复合结构';
                    }
                }
            }
            
            // 额外的复杂度检查
            const commaCount = (cleanSentence.match(/,/g) || []).length;
            const wordCount = words.length;
            
            if (wordCount > 25 && commaCount > 2) {
                complexityLevel = 'Highly Complex';
                complexityReason = '长句含多个从句';
            } else if (wordCount > 20 && commaCount > 1) {
                if (complexityLevel === 'Simple') {
                    complexityLevel = 'Complex Structure';
                    complexityReason = '较长且含从句';
                }
            }
            
            // 检查是否包含被动语态
            if (/\b(is|are|was|were|be|been|being)\s+([\w]+ed|[\w]+en)\b/.test(cleanSentence.toLowerCase())) {
                if (complexityLevel === 'Simple') {
                    complexityLevel = 'Complex Structure';
                    complexityReason = '含被动语态';
                }
            }
            
            // 只保留复杂的句子
            if (complexityLevel !== 'Simple') {
                complexSentences.push({
                    text: cleanSentence,
                    complexity: complexityLevel,
                    reason: complexityReason
                });
            }
        });
        
        // 根据英语水平过滤句子
        const levelFilter = {
            '4.0': ['Highly Complex', 'Advanced', 'Complex Structure'],
            '5.0': ['Highly Complex', 'Advanced', 'Complex Structure'],
            '6.0': ['Highly Complex', 'Advanced'],
            '7.0': ['Highly Complex']
        };
        
        const allowedLevels = levelFilter[this.englishLevel] || ['Highly Complex', 'Advanced'];
        const filteredSentences = complexSentences.filter(sentence => 
            allowedLevels.includes(sentence.complexity)
        );
        
        // 限制返回句子数量并排序（最复杂的在前）
        return filteredSentences
            .sort((a, b) => {
                const order = ['Highly Complex', 'Advanced', 'Complex Structure'];
                return order.indexOf(a.complexity) - order.indexOf(b.complexity);
            })
            .slice(0, Math.min(5, filteredSentences.length));
    }
    
    // 显示词汇分析结果
    displayVocabularyResults(vocabData, sentenceData, isFallback = false) {
        // 隐藏进度，显示内容
        this.vocabProgress.classList.add('d-none');
        this.vocabContent.classList.remove('d-none');
        
        // 更新计数
        this.vocabCount.textContent = vocabData.length;
        this.sentenceCount.textContent = sentenceData.length;
        
        // 如果是fallback模式，添加醒目提示
        if (isFallback) {
            this.addFallbackWarnings();
        } else {
            this.removeFallbackWarnings();
        }
        
        // 生成生词列表（初始显示基础信息）
        this.vocabList.innerHTML = vocabData.map((item, index) => `
            <div class="vocab-item" data-word="${item.word}" data-index="${index}">
                <div class="vocab-word">${item.word}</div>
                <div class="vocab-phonetic">
                    <span class="phonetic-text">${item.phonetic}</span>
                    <div class="phonetic-controls">
                        <button class="pronunciation-btn" data-word="${item.word}" data-accent="us" title="美音发音">
                            🇺🇸
                        </button>
                        <button class="pronunciation-btn" data-word="${item.word}" data-accent="uk" title="英音发音">
                            🇬🇧
                        </button>
                    </div>
                </div>
                <div class="vocab-definition-container">
                    <div class="vocab-definition basic-definition">${item.definition}</div>
                    <div class="detailed-definition d-none">
                        <div class="loading-indicator">
                            <i class="fas fa-spinner fa-spin me-2"></i>正在获取详细释义...
                        </div>
                    </div>
                </div>
                <span class="vocab-level ${item.level}">${this.getLevelText(item.level)}</span>
                <button class="btn btn-sm btn-outline-primary expand-btn mt-2" data-word="${item.word}">
                    <i class="fas fa-chevron-down me-1"></i>详细释义
                </button>
            </div>
        `).join('');
        
        // 绑定发音按钮事件
        this.bindPronunciationEvents();
        
        // 绑定批量播放按钮事件
        this.bindBatchPlayEvents();
        
        // 绑定详细释义展开按钮事件
        this.bindExpandButtonEvents();
        
        // 异步获取所有单词的详细释义
        this.preloadDetailedDefinitions(vocabData);
        
        // 生成复杂句子列表
        this.sentenceList.innerHTML = sentenceData.map(item => `
            <div class="sentence-item">
                <div class="sentence-text">${item.text}</div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <span class="sentence-complexity">${item.complexity}</span>
                    ${item.reason ? `<small class="text-muted">${item.reason}</small>` : ''}
                </div>
            </div>
        `).join('');
        
        // 添加动画效果
        this.vocabContent.classList.add('fade-in');
    }
    
    // 获取难度级别文本
    getLevelText(level) {
        const levelMap = {
            'high': '高难度',
            'medium': '中等',
            'advanced': '高级'
        };
        return levelMap[level] || '中等';
    }
    
    // 添加fallback模式的警告提示
    addFallbackWarnings() {
        // 为生词标题添加警告
        const vocabHeader = document.querySelector('.text-primary');
        if (vocabHeader && !vocabHeader.querySelector('.fallback-warning')) {
            const warningBadge = document.createElement('span');
            warningBadge.className = 'fallback-warning badge bg-warning text-dark ms-2 small';
            warningBadge.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>离线模式';
            vocabHeader.appendChild(warningBadge);
        }
        
        // 为复杂句子标题添加警告
        const sentenceHeader = document.querySelector('.text-success');
        if (sentenceHeader && !sentenceHeader.querySelector('.fallback-warning')) {
            const warningBadge = document.createElement('span');
            warningBadge.className = 'fallback-warning badge bg-warning text-dark ms-2 small';
            warningBadge.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>离线模式';
            sentenceHeader.appendChild(warningBadge);
        }
        
        // 在词汇列表顶部添加详细说明
        if (!document.querySelector('.fallback-notice')) {
            const notice = document.createElement('div');
            notice.className = 'fallback-notice alert alert-warning alert-dismissible fade show mb-3';
            notice.innerHTML = `
                <i class="fas fa-wifi me-2"></i>
                <strong>提示：</strong>服务器词汇分析暂时不可用，正在使用本地分析模式。
                <small class="d-block mt-1">
                    本地模式可能无法提供最准确的难度评估和中文释义，建议稍后重试或检查网络连接。
                </small>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            this.vocabList.parentNode.insertBefore(notice, this.vocabList);
        }
    }
    
    // 移除fallback模式的警告提示
    removeFallbackWarnings() {
        // 移除标题中的警告标记
        document.querySelectorAll('.fallback-warning').forEach(el => el.remove());
        
        // 移除详细说明
        const notice = document.querySelector('.fallback-notice');
        if (notice) {
            notice.remove();
        }
    }
    
    // 设置发音偏好
    setAccentPreference(accent) {
        this.accentPreference = accent;
        
        // 保存到cookie
        this.setCookie('accentPreference', accent);
        
        this.updateAccentUI();
        
        // 清空音频缓存以重新加载
        this.audioCache.clear();
    }
    
    // 更新发音偏好UI
    updateAccentUI() {
        const usCheck = document.getElementById('accentUS')?.querySelector('.fa-check');
        const ukCheck = document.getElementById('accentUK')?.querySelector('.fa-check');
        
        if (usCheck) usCheck.classList.toggle('d-none', this.accentPreference !== 'us');
        if (ukCheck) ukCheck.classList.toggle('d-none', this.accentPreference !== 'uk');
    }
    
    // 更新英语水平UI
    updateEnglishLevelUI() {
        document.querySelectorAll('[data-level]').forEach(item => {
            item.classList.toggle('active', item.dataset.level === this.englishLevel);
        });
    }
    
    // 绑定发音按钮事件
    bindPronunciationEvents() {
        document.querySelectorAll('.pronunciation-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const word = btn.dataset.word;
                const accent = btn.dataset.accent;
                this.playPronunciation(word, accent, btn);
            });
        });
    }
    
    // 绑定批量播放按钮事件
    bindBatchPlayEvents() {
        const playAllUSBtn = document.getElementById('playAllUS');
        const playAllUKBtn = document.getElementById('playAllUK');
        
        if (playAllUSBtn) {
            playAllUSBtn.addEventListener('click', () => {
                this.playAllPronunciations('us');
            });
        }
        
        if (playAllUKBtn) {
            playAllUKBtn.addEventListener('click', () => {
                this.playAllPronunciations('uk');
            });
        }
    }
    
    // 播放发音
    async playPronunciation(word, accent, button) {
        if (button.classList.contains('loading') || button.classList.contains('playing')) {
            return;
        }
        
        try {
            // 设置加载状态
            button.classList.add('loading');
            button.disabled = true;
            
            // 检查缓存
            const cacheKey = `${word}_${accent}`;
            let audio = this.audioCache.get(cacheKey);
            
            if (!audio) {
                // 创建音频对象
                audio = await this.loadAudio(word, accent);
                this.audioCache.set(cacheKey, audio);
            }
            
            // 清除加载状态
            button.classList.remove('loading');
            button.disabled = false;
            
            // 设置播放状态
            button.classList.add('playing');
            
            // 播放音频
            audio.currentTime = 0;
            await audio.play();
            
            // 播放完成后清除状态
            audio.addEventListener('ended', () => {
                button.classList.remove('playing');
            }, { once: true });
            
        } catch (error) {
            console.error('发音播放失败:', error);
            
            // 清除状态
            button.classList.remove('loading', 'playing');
            button.disabled = false;
            
            // 显示错误提示
            this.showToast('error', '发音加载失败，请检查网络连接');
        }
    }
    
    // 加载音频
    async loadAudio(word, accent) {
        return new Promise((resolve, reject) => {
            const audio = new Audio();
            
            // 使用免费的发音API服务
            const apiUrl = this.getPronunciationUrl(word, accent);
            audio.src = apiUrl;
            
            audio.addEventListener('canplay', () => {
                resolve(audio);
            }, { once: true });
            
            audio.addEventListener('error', (e) => {
                reject(new Error('音频加载失败'));
            }, { once: true });
            
            // 开始预加载
            audio.preload = 'auto';
            audio.load();
        });
    }
    
    // 获取发音API URL
    getPronunciationUrl(word, accent) {
        // 使用多个免费发音服务作为备选
        const services = {
            // Google Translate TTS (免费且稳定)
            google: (word, accent) => {
                const lang = accent === 'uk' ? 'en-gb' : 'en-us';
                return `https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q=${encodeURIComponent(word)}&tl=${lang}`;
            },
            
            // Oxford Dictionaries (备用)
            oxford: (word, accent) => {
                const region = accent === 'uk' ? 'uk' : 'us';
                return `https://od-api.oxforddictionaries.com/api/v2/entries/en-${region}/${word.toLowerCase()}/pronunciations`;
            },
            
            // Forvo (备用)
            forvo: (word, accent) => {
                const country = accent === 'uk' ? 'gbr' : 'usa';
                return `https://apifree.forvo.com/key/pronunciation/${word}/en_${country}`;
            }
        };
        
        // 默认使用Google TTS
        return services.google(word, accent);
    }
    
    // 播放所有单词发音（批量播放功能）
    async playAllPronunciations(accent = null) {
        const targetAccent = accent || this.accentPreference;
        const buttons = document.querySelectorAll(`.pronunciation-btn[data-accent="${targetAccent}"]`);
        
        for (let i = 0; i < buttons.length; i++) {
            const button = buttons[i];
            const word = button.dataset.word;
            
            try {
                await this.playPronunciation(word, targetAccent, button);
                
                // 等待播放完成再播放下一个
                await new Promise(resolve => {
                    const audio = this.audioCache.get(`${word}_${targetAccent}`);
                    if (audio) {
                        audio.addEventListener('ended', resolve, { once: true });
                    } else {
                        setTimeout(resolve, 1000);
                    }
                });
                
                // 短暂延迟
                await new Promise(resolve => setTimeout(resolve, 500));
                
            } catch (error) {
                console.error(`播放 ${word} 失败:`, error);
            }
        }
    }
    
    // 绑定详细释义展开按钮事件
    bindExpandButtonEvents() {
        this.vocabList.addEventListener('click', async (e) => {
            if (e.target.classList.contains('expand-btn') || e.target.closest('.expand-btn')) {
                const button = e.target.classList.contains('expand-btn') ? e.target : e.target.closest('.expand-btn');
                const word = button.dataset.word;
                const vocabItem = button.closest('.vocab-item');
                const detailedDiv = vocabItem.querySelector('.detailed-definition');
                const iconElement = button.querySelector('i');
                
                if (detailedDiv.classList.contains('d-none')) {
                    // 展开详细释义
                    detailedDiv.classList.remove('d-none');
                    iconElement.className = 'fas fa-chevron-up me-1';
                    button.innerHTML = '<i class="fas fa-chevron-up me-1"></i>收起';
                    
                    // 如果还没有加载详细释义，则加载
                    if (!detailedDiv.dataset.loaded) {
                        await this.loadWordDefinition(word, detailedDiv);
                    }
                } else {
                    // 收起详细释义
                    detailedDiv.classList.add('d-none');
                    iconElement.className = 'fas fa-chevron-down me-1';
                    button.innerHTML = '<i class="fas fa-chevron-down me-1"></i>详细释义';
                }
            }
        });
    }
    
    // 预加载所有单词的详细释义（后台异步进行）
    async preloadDetailedDefinitions(vocabData) {
        console.log('🔄 开始预加载词汇详细释义...');
        
        // 限制并发请求数量，避免API限制
        const batchSize = 3;
        for (let i = 0; i < vocabData.length; i += batchSize) {
            const batch = vocabData.slice(i, i + batchSize);
            
            // 并行处理当前批次
            await Promise.all(
                batch.map(async (item) => {
                    try {
                        const definition = await this.fetchWordDefinition(item.word);
                        if (definition) {
                            // 缓存结果
                            this.definitionCache.set(item.word, definition);
                            console.log(`✅ 预加载 ${item.word} 释义完成`);
                        }
                    } catch (error) {
                        console.warn(`⚠️ 预加载 ${item.word} 释义失败:`, error);
                    }
                })
            );
            
            // 批次间稍作停顿，避免过于频繁的请求
            if (i + batchSize < vocabData.length) {
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }
        
        console.log('✅ 词汇详细释义预加载完成');
    }
    
    // 加载单个单词的详细释义
    async loadWordDefinition(word, containerElement) {
        try {
            // 显示加载中状态
            containerElement.innerHTML = `
                <div class="loading-indicator">
                    <i class="fas fa-spinner fa-spin me-2"></i>正在获取详细释义...
                </div>
            `;
            
            // 从缓存或API获取释义
            let definition = this.definitionCache.get(word);
            if (!definition) {
                definition = await this.fetchWordDefinition(word);
                if (definition) {
                    this.definitionCache.set(word, definition);
                }
            }
            
            if (definition) {
                // 显示详细释义
                containerElement.innerHTML = this.renderDetailedDefinition(definition);
                containerElement.dataset.loaded = 'true';
            } else {
                // 显示错误信息
                containerElement.innerHTML = `
                    <div class="alert alert-warning mb-0">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        暂时无法获取该单词的详细释义，请稍后重试。
                    </div>
                `;
            }
            
        } catch (error) {
            console.error(`加载 ${word} 释义失败:`, error);
            containerElement.innerHTML = `
                <div class="alert alert-danger mb-0">
                    <i class="fas fa-times me-2"></i>
                    获取释义时出现错误: ${error.message}
                </div>
            `;
        }
    }
    
    // 从API获取单词定义
    async fetchWordDefinition(word) {
        try {
            const response = await fetch(`/api/dictionary/${encodeURIComponent(word)}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 10000
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    return result.data;
                } else {
                    console.warn(`API返回错误: ${result.error}`);
                    return null;
                }
            } else {
                console.error(`HTTP错误: ${response.status} ${response.statusText}`);
                return null;
            }
            
        } catch (error) {
            console.error(`请求词典API失败:`, error);
            return null;
        }
    }
    
    // 渲染详细释义内容
    renderDetailedDefinition(definition) {
        const { word, phonetics, definitions, examples, synonyms, etymology, related_words, source } = definition;
        
        let html = `
            <div class="detailed-definition-content">
                <div class="definition-header mb-3">
                    <h6 class="mb-1">${word}</h6>
                    ${phonetics && phonetics.length > 0 ? 
                        `<div class="phonetics text-muted">${phonetics.join(' / ')}</div>` : ''}
                </div>
        `;
        
        // 主要释义
        if (definitions && definitions.length > 0) {
            html += `
                <div class="definitions-section mb-3">
                    <h6 class="section-title">📖 主要释义</h6>
                    <div class="definitions-list">
            `;
            
            definitions.forEach((def, index) => {
                html += `
                    <div class="definition-item mb-2">
                        <div class="definition-header">
                            <span class="badge bg-secondary me-2">${def.partOfSpeech || 'n.'}</span>
                            <span class="definition-text">${def.definition}</span>
                        </div>
                        ${def.example ? `<div class="example-text text-muted mt-1"><em>例句: ${def.example}</em></div>` : ''}
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        }
        
        // 词根信息
        if (etymology) {
            html += `
                <div class="etymology-section mb-3">
                    <h6 class="section-title">🌱 词根信息</h6>
                    <div class="etymology-content">
                        <div class="root-info">
                            <strong>${etymology.root}</strong> - ${etymology.meaning}
                        </div>
                        <div class="related-examples mt-2">
                            <small class="text-muted">同词根词汇: </small>
                            ${etymology.examples.map(word => `<span class="badge bg-light text-dark me-1">${word}</span>`).join('')}
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 近义词
        if (synonyms && synonyms.length > 0) {
            html += `
                <div class="synonyms-section mb-3">
                    <h6 class="section-title">🔗 近义词</h6>
                    <div class="synonyms-list">
                        ${synonyms.map(syn => `<span class="badge bg-info text-light me-1">${syn}</span>`).join('')}
                    </div>
                </div>
            `;
        }
        
        // 相关词汇
        if (related_words && related_words.length > 0) {
            html += `
                <div class="related-words-section mb-3">
                    <h6 class="section-title">🔄 相关词汇</h6>
                    <div class="related-words-list">
                        ${related_words.map(word => `<span class="badge bg-outline-primary me-1">${word}</span>`).join('')}
                    </div>
                </div>
            `;
        }
        
        // 例句（如果有额外的例句）
        if (examples && examples.length > 0) {
            html += `
                <div class="examples-section mb-3">
                    <h6 class="section-title">💭 更多例句</h6>
                    <div class="examples-list">
            `;
            
            examples.forEach(example => {
                html += `<div class="example-item mb-1"><em>"${example}"</em></div>`;
            });
            
            html += `
                    </div>
                </div>
            `;
        }
        
        // 数据源信息
        html += `
                <div class="source-info mt-3 pt-2 border-top">
                    <small class="text-muted">
                        <i class="fas fa-database me-1"></i>数据来源: ${source}
                    </small>
                </div>
            </div>
        `;
        
        return html;
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    const app = new PodcastTranscriber();
    
    // 全局错误处理
    window.addEventListener('error', (e) => {
        console.error('Global error:', e.error);
    });
    
    // 控制台欢迎信息
    console.log('%c🎙️ Podcast Transcriber Web App', 'color: #007bff; font-size: 16px; font-weight: bold;');
    console.log('GitHub: https://github.com/your-repo');
});