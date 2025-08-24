# 🎙️ Podcast Transcriber & Downloader

A comprehensive Python toolkit for downloading podcasts and transcribing audio with advanced speaker identification capabilities.

## ✨ Features

### 📥 Podcast Downloader
- Download podcasts from Apple Podcasts URLs
- Support for RSS feeds and direct audio links
- Automatic RSS feed extraction from iTunes API
- Browser cookie authentication for premium content
- Batch downloading with customizable episode limits

### 🎤 Audio Transcription
- High-accuracy transcription using OpenAI Whisper
- Advanced speaker diarization (identification & separation) 
- Multiple output formats: TXT, SRT, VTT, JSON
- Audio preprocessing for optimal quality
- Support for multiple languages

### 🔊 Speaker Identification
- **Premium Mode**: pyannote.audio for professional-grade speaker separation
- **Fallback Mode**: Pattern-based speaker detection
- Clear speaker labeling (A:, B:, C:, etc.)
- Intelligent content grouping per speaker

## 🚀 Quick Start

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/podcast-transcriber.git
   cd podcast-transcriber
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Basic Usage

1. **Download a podcast**
   ```bash
   python podcast_downloader.py "https://podcasts.apple.com/us/podcast/name/id123456789"
   ```

2. **Transcribe with speaker identification**
   ```bash
   python audio_transcriber.py "your_audio_file.mp3"
   ```

## 📖 Documentation

- [**Authentication Guide**](AUTHENTICATION.md) - Setup for premium speaker identification
- [**Usage Guide**](USAGE.md) - Detailed usage instructions and examples

## 🛠️ Advanced Configuration

### Speaker Identification Setup

For the best speaker identification results, configure pyannote.audio authentication:

1. **Quick setup**
   ```bash
   python setup_auth.py
   ```

2. **Manual setup**
   - Get a Hugging Face token: https://hf.co/settings/tokens
   - Accept model terms: https://hf.co/pyannote/speaker-diarization-3.1
   - Set token: `echo "HF_TOKEN=your_token" > .env`

### Commands Reference

```bash
# Download podcasts
python podcast_downloader.py [URL] [-n episodes] [-o output_dir]

# Transcribe audio
python audio_transcriber.py [file] [-f format] [-m model] [--no-diarization]

# Options:
# -f, --format: txt, srt, vtt, json
# -m, --model: tiny, base, small, medium, large
# -o, --output: output directory
# -n, --max-episodes: number of episodes to download
```

## 📁 Project Structure

```
podcast-transcriber/
├── 📜 podcast_downloader.py    # Podcast downloading
├── 🎤 audio_transcriber.py     # Audio transcription + speaker ID
├── 🔐 setup_auth.py           # Authentication setup
├── 🧪 test_auth.py            # Test authentication
├── 📋 requirements.txt        # Python dependencies
├── 📚 USAGE.md               # Detailed usage guide
├── 🔑 AUTHENTICATION.md      # Authentication setup
└── 📁 downloads/             # Downloaded files (created automatically)
```

## 🎯 Example Output

### Speaker-Separated Transcript
```
A: Welcome to our podcast! Today we're discussing AI and machine learning.

B: Thanks for having me. I'm excited to share my thoughts on this topic.

A: Let's start with the basics. What exactly is machine learning?

B: Well, machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed for every task.
```

### SRT Subtitles with Speakers
```
1
00:00:00,000 --> 00:00:05,000
A: Welcome to our podcast! Today we're discussing AI and machine learning.

2
00:00:05,000 --> 00:00:10,000
B: Thanks for having me. I'm excited to share my thoughts on this topic.
```

## 🔧 Requirements

- **Python**: 3.8+
- **System**: macOS, Linux, Windows
- **Dependencies**: Listed in `requirements.txt`
- **Optional**: Hugging Face account for premium speaker identification

## 🌟 Key Technologies

- **[OpenAI Whisper](https://openai.com/research/whisper)**: State-of-the-art speech recognition
- **[pyannote.audio](https://github.com/pyannote/pyannote-audio)**: Speaker diarization
- **[PyTorch](https://pytorch.org/)**: Deep learning framework
- **[Hugging Face](https://huggingface.co/)**: Model hosting and authentication

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal Disclaimer

This tool is for personal use only. Users are responsible for:
- Complying with copyright laws
- Respecting terms of service of podcast platforms  
- Only downloading content they have legal access to

## 🙏 Acknowledgments

- OpenAI for the Whisper model
- pyannote team for speaker diarization
- All podcast creators and platforms