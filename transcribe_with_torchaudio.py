#!/usr/bin/env python3
"""
Temporary transcription script using torchaudio instead of ffmpeg
"""

import torch
import torchaudio
import whisper
import numpy as np

def transcribe_with_torchaudio(audio_path, output_path):
    print(f"🎤 Loading audio: {audio_path}")
    
    # Load audio using torchaudio
    waveform, sample_rate = torchaudio.load(audio_path)
    audio = waveform.numpy().flatten()
    
    print(f"📊 Sample rate: {sample_rate}Hz")
    
    # Convert to 16kHz if needed for optimal Whisper performance
    if sample_rate != 16000:
        print("🔄 Resampling to 16kHz...")
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        waveform = resampler(waveform)
        audio = waveform.numpy().flatten()
    
    # Load whisper model and transcribe
    print("🔧 Loading Whisper model...")
    model = whisper.load_model('base')
    
    print("📝 Transcribing...")
    result = model.transcribe(audio)
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result['text'])
    
    print(f"✅ Transcription completed!")
    print(f"📄 Saved to: {output_path}")
    return result

if __name__ == "__main__":
    transcribe_with_torchaudio(
        "downloads/AEE One Passionate Way to Share Your Likes and Dislikes in English.mp3",
        "downloads/transcript.txt"
    )