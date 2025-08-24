# pyannote.audio 认证指南

pyannote 的高级说话人识别模型需要 Hugging Face 认证才能使用。

## 快速设置（推荐）

### 方法 1：使用认证脚本
```bash
python setup_auth.py
```

### 方法 2：手动设置

1. **获取 Token**
   - 访问：https://hf.co/settings/tokens
   - 创建新的 "Read" 权限 token
   - 复制 token

2. **接受模型条款**
   - 访问：https://hf.co/pyannote/speaker-diarization-3.1
   - 点击 "Agree and access repository"
   - 访问：https://hf.co/pyannote/segmentation-3.0
   - 点击 "Agree and access repository"

3. **配置 Token**
   
   **选项 A：环境变量**
   ```bash
   export HF_TOKEN="your_token_here"
   ```
   
   **选项 B：创建 .env 文件**
   ```bash
   echo "HF_TOKEN=your_token_here" > .env
   ```
   
   **选项 C：Hugging Face 默认位置**
   ```bash
   mkdir -p ~/.huggingface
   echo "your_token_here" > ~/.huggingface/token
   ```

## 测试认证

```bash
python setup_auth.py
# 选择选项 2 测试认证
```

## 使用说话人识别

认证成功后：

```bash
# 启用高精度说话人识别（需要认证）
python audio_transcriber.py "podcast.mp3"

# 如果不想使用认证，使用简单模式
python audio_transcriber.py --no-diarization "podcast.mp3"
```

## 认证状态

- ✅ **已认证**：使用 pyannote 高精度模型，支持多说话人精确识别
- ❌ **未认证**：使用基于音频停顿的简单说话人分离（A/B 模式）

## 常见问题

### 1. "gated repository" 错误
- 需要访问模型页面接受使用条款
- 确保登录的账户已接受条款

### 2. "Invalid token" 错误
- 检查 token 是否正确复制
- 确保 token 有 "Read" 权限

### 3. 找不到 token 文件
- 确保 .env 文件在项目根目录
- 检查环境变量是否设置

## 隐私说明

- Token 仅用于访问 Hugging Face 模型
- 不会上传或共享您的音频文件
- 所有处理都在本地完成