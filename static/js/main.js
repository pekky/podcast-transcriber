// Podcast Transcriber Web App JavaScript

class PodcastTranscriber {
    constructor() {
        this.currentDownloadTask = null;
        this.currentTranscribeTask = null;
        this.audioFile = null;
        
        this.initializeElements();
        this.bindEvents();
        this.showToast = this.showToast.bind(this);
    }
    
    initializeElements() {
        // 下载相关元素
        this.urlInput = document.getElementById('urlInput');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.downloadProgress = document.getElementById('downloadProgress');
        this.downloadStatus = document.getElementById('downloadStatus');
        this.downloadResult = document.getElementById('downloadResult');
        this.audioFileName = document.getElementById('audioFileName');
        this.downloadLink = document.getElementById('downloadLink');
        
        // 转录相关元素
        this.withSpeakers = document.getElementById('withSpeakers');
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
        
        // Toast 元素
        this.successToast = new bootstrap.Toast(document.getElementById('successToast'));
        this.errorToast = new bootstrap.Toast(document.getElementById('errorToast'));
    }
    
    bindEvents() {
        // URL 输入变化
        this.urlInput.addEventListener('input', () => {
            const hasUrl = this.urlInput.value.trim().length > 0;
            this.downloadBtn.disabled = !hasUrl;
            
            if (hasUrl) {
                this.downloadBtn.innerHTML = '<i class="fas fa-download"></i>';
            }
        });
        
        // 下载按钮点击
        this.downloadBtn.addEventListener('click', () => {
            this.startDownload();
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
            
            this.showToast('success', '音频下载完成！');
        } else {
            throw new Error(result.error || '下载失败');
        }
        
        this.resetDownloadUI();
    }
    
    resetDownloadUI() {
        this.downloadBtn.disabled = false;
        this.downloadBtn.innerHTML = '<i class="fas fa-download"></i>';
        this.currentDownloadTask = null;
    }
    
    async startTranscribe() {
        if (!this.audioFile) {
            this.showToast('error', '请先下载音频文件');
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
            
            // 发送转录请求
            const response = await fetch('/api/transcribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    audio_file: this.audioFile,
                    with_speakers: this.withSpeakers.checked
                })
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
    
    displayTranscript(text) {
        // 隐藏空状态
        this.emptyState.classList.add('d-none');
        this.transcriptContent.classList.remove('d-none');
        
        // 格式化转录文本
        const formattedText = this.formatTranscript(text);
        this.transcriptText.innerHTML = formattedText;
        
        // 添加动画效果
        this.transcriptContent.classList.add('fade-in');
        
        // 滚动到顶部
        this.transcriptText.scrollTop = 0;
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