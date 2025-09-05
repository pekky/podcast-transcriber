#!/usr/bin/env python3
"""
Enhanced transcription with speaker identification using torchaudio
"""

import torch
import torchaudio
import whisper
import numpy as np
from pathlib import Path
import time

def simple_speaker_detection(segments):
    """
    Simple speaker detection based on pauses between segments
    """
    enhanced_segments = []
    current_speaker = 'A'
    last_end = 0
    
    for i, segment in enumerate(segments):
        # If there's a significant pause (>2 seconds), possibly change speaker
        if segment['start'] - last_end > 2.0 and i > 0:
            # Simple alternation between A and B
            current_speaker = 'B' if current_speaker == 'A' else 'A'
        
        enhanced_segment = segment.copy()
        enhanced_segment['speaker'] = current_speaker
        enhanced_segments.append(enhanced_segment)
        
        last_end = segment['end']
    
    return enhanced_segments

def transcribe_with_speakers(audio_path, output_path):
    print(f"🎤 Loading audio: {audio_path}")
    
    # Load audio using torchaudio
    waveform, sample_rate = torchaudio.load(audio_path)
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
    
    print("📝 Transcribing with speaker detection...")
    result = model.transcribe(audio)
    
    # Add simple speaker detection
    enhanced_segments = simple_speaker_detection(result['segments'])
    
    # Save speaker-formatted transcript
    with open(output_path, 'w', encoding='utf-8') as f:
        for segment in enhanced_segments:
            speaker = segment['speaker']
            text = segment['text'].strip()
            if text:
                f.write(f"{speaker}: {text}\n\n")
    
    print(f"✅ Transcription with speakers completed!")
    print(f"📄 Saved to: {output_path}")
    return result

if __name__ == "__main__":
    transcribe_with_speakers(
        "downloads/AEE One Passionate Way to Share Your Likes and Dislikes in English.mp3",
        "downloads/transcript_with_speakers.txt"
    )