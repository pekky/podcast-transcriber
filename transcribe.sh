#!/bin/bash
# Audio Transcriber Launcher Script
# This script ensures ffmpeg is in PATH before running the transcriber

# Add ffmpeg to PATH
export PATH="/Users/binqianglai/bin:$PATH"

# Run the audio transcriber with all arguments passed through
python3 "$(dirname "$0")/audio_transcriber.py" "$@"