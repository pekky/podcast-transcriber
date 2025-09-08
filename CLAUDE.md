# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based podcast transcriber and downloader toolkit with three main components:

1. **Podcast Downloader** (`podcast_downloader.py`): Downloads podcasts from Apple Podcasts URLs, RSS feeds, and direct audio links
2. **Audio Transcriber** (`audio_transcriber.py`): Transcribes audio using OpenAI Whisper with optional speaker diarization via pyannote.audio
3. **Vocabulary Analyzer** (`vocabulary_analyzer.py`): Extracts and analyzes vocabulary from transcripts to create study guides for English learners

## Key Architecture

- **Main Scripts**: Two standalone CLI tools that can be used independently
- **Speaker Identification**: Two-tier system - premium pyannote.audio (requires HF auth) with fallback to pattern-based detection
- **Authentication**: Hugging Face token management via environment variables, .env files, or ~/.huggingface/token
- **Audio Processing**: Optional preprocessing pipeline using pydub for optimal Whisper performance

## Development Commands

### Running the Tools
```bash
# Download podcast (single episode)
python3 podcast_downloader.py "https://podcasts.apple.com/us/podcast/name/id123456789"

# Download multiple episodes
python3 podcast_downloader.py -n 5 -o output_dir "https://example.com/feed.rss"

# Interactive mode - prompts for URL and filename
python3 podcast_downloader.py

# Interactive mode - select from downloads directory
python3 audio_transcriber.py

# Transcribe with speaker identification
python3 audio_transcriber.py "audio.mp3"

# Transcribe to different formats
python3 audio_transcriber.py -f srt "audio.mp3"
python3 audio_transcriber.py -f json --no-diarization "audio.mp3"

# Vocabulary analysis from transcripts
python3 vocabulary_analyzer.py "downloads/transcript_speakers.txt"
python3 vocabulary_analyzer.py "transcript.txt" -l "6.0-6.5" -m 25
```

### Testing Authentication
```bash
python3 test_auth.py  # Test pyannote.audio authentication
python3 setup_auth.py  # Setup HF authentication interactively
```

### Dependencies
Install via: `pip install -r requirements.txt`

Core dependencies:
- `openai-whisper`: Speech-to-text transcription
- `pyannote.audio`: Speaker diarization (optional, requires HF auth)
- `pydub`: Audio preprocessing (optional)
- `torch`: Required by Whisper and pyannote

## File Structure

- `podcast_downloader.py`: Main downloader with Apple Podcasts and RSS support
- `audio_transcriber.py`: Main transcriber with AudioTranscriber class
- `setup_auth.py`: Interactive HF authentication setup
- `test_auth.py`: Authentication testing utility
- `extract_cookies.py`: Browser cookie extraction for Apple Podcasts auth
- `downloads/`: Default output directory (auto-created)

## Authentication System

The transcriber uses a hierarchical token discovery system:
1. Environment variables: `HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN`
2. Local `.env` file: `HF_TOKEN=your_token`
3. HF cache: `~/.huggingface/token`

Required HF model access:
- https://hf.co/pyannote/speaker-diarization-3.1
- https://hf.co/pyannote/segmentation-3.0

## Output Formats

- **TXT**: Speaker-formatted text with sentence-by-sentence breakdown
- **SRT**: Subtitle format with speaker labels and timestamps
- **VTT**: WebVTT format for web players
- **JSON**: Full Whisper output with speaker assignments

## Error Handling Patterns

Both tools include comprehensive error handling for:
- Authentication failures (401/403 responses)
- Network issues and timeouts
- Missing dependencies with helpful install messages
- File access and permission issues