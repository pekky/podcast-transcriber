#!/usr/bin/env python3
"""
Transcribe YouTube audio file
"""

import torch
import torchaudio
import whisper
import numpy as np

def transcribe_youtube_audio():
    print("🎤 Loading YouTube audio: Me at the zoo.m4a")
    
    # Load audio using torchaudio
    waveform, sample_rate = torchaudio.load("downloads/Me at the zoo.m4a")
    audio = waveform.numpy().flatten()
    
    print(f"📊 Sample rate: {sample_rate}Hz")
    
    # Convert to 16kHz if needed
    if sample_rate != 16000:
        print("🔄 Resampling to 16kHz...")
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        waveform = resampler(waveform)
        audio = waveform.numpy().flatten()
    
    # Load whisper model and transcribe
    print("🔧 Loading Whisper model...")
    model = whisper.load_model('base')
    
    print("📝 Transcribing YouTube audio...")
    result = model.transcribe(audio)
    
    # Save to file
    with open("downloads/youtube_transcript.txt", 'w', encoding='utf-8') as f:
        f.write(result['text'])
    
    print(f"✅ YouTube transcription completed!")
    print(f"📄 Saved to: downloads/youtube_transcript.txt")
    print(f"🎯 Transcript: {result['text']}")
    return result

if __name__ == "__main__":
    transcribe_youtube_audio()