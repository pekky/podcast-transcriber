#!/usr/bin/env python3
"""
Audio Transcription Tool

This script transcribes audio files (MP3, WAV, M4A, etc.) to text using OpenAI's Whisper model.
Perfect for transcribing downloaded podcast episodes.
"""

import os
import sys
import argparse
from pathlib import Path
import time
import json
from typing import Optional, List, Dict, Tuple
import warnings
import numpy as np
import re

# Suppress some warnings
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import whisper
except ImportError:
    print("❌ Whisper not installed. Please install it with:")
    print("pip install openai-whisper")
    sys.exit(1)

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️  pydub not available. Some audio preprocessing features will be limited.")
    print("Install with: pip install pydub")

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    print("⚠️  pyannote.audio not available. Speaker diarization will be disabled.")
    print("Install with: pip install pyannote.audio")


class AudioTranscriber:
    def __init__(self, model_size: str = "base", device: str = "auto", enable_diarization: bool = True):
        """
        Initialize the transcriber.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (auto, cpu, cuda)
            enable_diarization: Enable speaker diarization
        """
        self.model_size = model_size
        self.device = device
        self.model = None
        self.diarization_pipeline = None
        self.enable_diarization = enable_diarization and PYANNOTE_AVAILABLE
        
        print(f"🔧 Initializing Whisper model: {model_size}")
        self._load_model()
        
        if self.enable_diarization:
            self._load_diarization_pipeline()
    
    def _load_model(self):
        """Load the Whisper model."""
        try:
            self.model = whisper.load_model(
                self.model_size, 
                device=self.device if self.device != "auto" else None
            )
            print(f"✅ Whisper model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading Whisper model: {e}")
            sys.exit(1)
    
    def _get_hf_token(self) -> Optional[str]:
        """Get Hugging Face token from various sources."""
        # Try environment variable first
        token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_HUB_TOKEN')
        if token:
            return token
        
        # Try .env file
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('HF_TOKEN='):
                        return line.split('=', 1)[1].strip()
        
        # Try huggingface hub cache
        hf_token_file = Path.home() / '.huggingface' / 'token'
        if hf_token_file.exists():
            try:
                with open(hf_token_file, 'r') as f:
                    return f.read().strip()
            except:
                pass
        
        return None
    
    def _load_diarization_pipeline(self):
        """Load the speaker diarization pipeline."""
        try:
            print("🔧 Initializing speaker diarization pipeline...")
            
            # Get authentication token
            token = self._get_hf_token()
            
            if not token:
                print("⚠️  No Hugging Face token found.")
                print("   Run 'python setup_auth.py' to configure authentication.")
                print("   Using fallback speaker detection instead.")
                self.enable_diarization = False
                self.diarization_pipeline = None
                return
            
            # Try to load the pipeline with authentication
            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=token
            )
            print("✅ Speaker diarization pipeline loaded successfully")
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "gated" in error_msg or "accept the user conditions" in error_msg:
                print(f"⚠️  Model access denied: {e}")
                print("   Please visit: https://hf.co/pyannote/speaker-diarization-3.1")
                print("   Accept the user conditions, then try again.")
            elif "authentication" in error_msg or "token" in error_msg:
                print(f"⚠️  Authentication failed: {e}")
                print("   Run 'python setup_auth.py' to configure your token.")
            else:
                print(f"⚠️  Could not load diarization pipeline: {e}")
            
            print("   Using fallback speaker detection instead.")
            self.enable_diarization = False
            self.diarization_pipeline = None
    
    def preprocess_audio(self, audio_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Preprocess audio file for better transcription.
        
        Args:
            audio_path: Input audio file path
            output_path: Output preprocessed file path
            
        Returns:
            Path to preprocessed file
        """
        if not PYDUB_AVAILABLE:
            return audio_path
        
        if output_path is None:
            output_path = audio_path.parent / f"{audio_path.stem}_processed.wav"
        
        try:
            print("🔄 Preprocessing audio...")
            
            # Load audio
            audio = AudioSegment.from_file(str(audio_path))
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
                print("   📻 Converted to mono")
            
            # Set sample rate to 16kHz (optimal for Whisper)
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
                print(f"   🎵 Resampled to 16kHz (was {audio.frame_rate}Hz)")
            
            # Normalize audio levels
            audio = audio.normalize()
            print("   🔊 Normalized audio levels")
            
            # Export as WAV
            audio.export(str(output_path), format="wav")
            print(f"   💾 Saved preprocessed audio: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"⚠️  Preprocessing failed: {e}")
            return audio_path
    
    def perform_diarization(self, audio_path: Path) -> Optional[Dict]:
        """
        Perform speaker diarization on audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Diarization result or None if failed
        """
        if not self.enable_diarization or not self.diarization_pipeline:
            return None
        
        try:
            print("👥 Performing speaker diarization...")
            diarization = self.diarization_pipeline(str(audio_path))
            
            # Convert to a more usable format
            speakers = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': speaker
                })
            
            print(f"✅ Found {len(set(s['speaker'] for s in speakers))} speakers")
            return {'speakers': speakers}
            
        except Exception as e:
            print(f"⚠️  Speaker diarization failed: {e}")
            return None
    
    def assign_speakers_to_segments(self, transcription: Dict, diarization: Optional[Dict]) -> Dict:
        """
        Assign speakers to transcription segments.
        
        Args:
            transcription: Whisper transcription result
            diarization: Speaker diarization result
            
        Returns:
            Enhanced transcription with speaker information
        """
        if not diarization or 'speakers' not in diarization:
            # No diarization available, assign generic speakers based on pauses
            return self._assign_generic_speakers(transcription)
        
        speakers_timeline = diarization['speakers']
        enhanced_segments = []
        
        for segment in transcription['segments']:
            segment_start = segment['start']
            segment_end = segment['end']
            segment_mid = (segment_start + segment_end) / 2
            
            # Find the speaker for this segment
            assigned_speaker = 'Unknown'
            for speaker_info in speakers_timeline:
                if speaker_info['start'] <= segment_mid <= speaker_info['end']:
                    assigned_speaker = speaker_info['speaker']
                    break
            
            # Convert speaker labels to A, B, C, etc.
            if assigned_speaker != 'Unknown':
                speaker_mapping = self._get_speaker_mapping(speakers_timeline)
                assigned_speaker = speaker_mapping.get(assigned_speaker, assigned_speaker)
            
            enhanced_segment = segment.copy()
            enhanced_segment['speaker'] = assigned_speaker
            enhanced_segments.append(enhanced_segment)
        
        result = transcription.copy()
        result['segments'] = enhanced_segments
        return result
    
    def _assign_generic_speakers(self, transcription: Dict) -> Dict:
        """
        Assign generic speakers (A, B, C) based on pauses and voice changes.
        This is a simple heuristic when diarization is not available.
        """
        enhanced_segments = []
        current_speaker = 'A'
        last_end = 0
        
        for i, segment in enumerate(transcription['segments']):
            # If there's a significant pause (>2 seconds), possibly change speaker
            if segment['start'] - last_end > 2.0 and i > 0:
                # Simple alternation between A and B
                current_speaker = 'B' if current_speaker == 'A' else 'A'
            
            enhanced_segment = segment.copy()
            enhanced_segment['speaker'] = current_speaker
            enhanced_segments.append(enhanced_segment)
            
            last_end = segment['end']
        
        result = transcription.copy()
        result['segments'] = enhanced_segments
        return result
    
    def _get_speaker_mapping(self, speakers_timeline: List[Dict]) -> Dict[str, str]:
        """
        Create a mapping from speaker IDs to A, B, C, etc.
        """
        unique_speakers = sorted(set(s['speaker'] for s in speakers_timeline))
        speaker_letters = [chr(ord('A') + i) for i in range(len(unique_speakers))]
        return dict(zip(unique_speakers, speaker_letters))
    
    def transcribe_audio(self, audio_path: Path, language: Optional[str] = None) -> Dict:
        """
        Transcribe audio file to text with speaker diarization.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'zh', 'es')
            
        Returns:
            Transcription result dictionary with speaker information
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"🎤 Transcribing: {audio_path.name}")
        start_time = time.time()
        
        try:
            # Step 1: Perform speaker diarization
            diarization = self.perform_diarization(audio_path) if self.enable_diarization else None
            
            # Step 2: Transcribe with Whisper
            print("📝 Transcribing speech to text...")
            result = self.model.transcribe(
                str(audio_path),
                language=language,
                verbose=False
            )
            
            # Step 3: Assign speakers to segments
            enhanced_result = self.assign_speakers_to_segments(result, diarization)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Transcription completed in {duration:.1f}s")
            return enhanced_result
            
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            raise
    
    def save_transcript(self, result: Dict, output_path: Path, format: str = "txt"):
        """
        Save transcription result to file with speaker identification.
        
        Args:
            result: Enhanced transcription result with speaker information
            output_path: Output file path
            format: Output format (txt, srt, vtt, json)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                self._write_speaker_formatted_text(result, f)
                
        elif format == "srt":
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(result["segments"], 1):
                    start = self._format_timestamp(segment["start"])
                    end = self._format_timestamp(segment["end"])
                    text = segment["text"].strip()
                    speaker = segment.get('speaker', 'Unknown')
                    
                    f.write(f"{i}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{speaker}: {text}\n\n")
                    
        elif format == "vtt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                for segment in result["segments"]:
                    start = self._format_timestamp(segment["start"], srt=False)
                    end = self._format_timestamp(segment["end"], srt=False)
                    text = segment["text"].strip()
                    speaker = segment.get('speaker', 'Unknown')
                    
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{speaker}: {text}\n\n")
                    
        elif format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Transcript saved: {output_path}")
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex patterns.
        Handles common abbreviations and edge cases.
        """
        if not text.strip():
            return []
        
        # Common abbreviations that shouldn't trigger sentence breaks
        abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|i\.e|e\.g|a\.m|p\.m|U\.S|U\.K)'
        
        # First, protect abbreviations by replacing periods with a placeholder
        protected_text = re.sub(f'({abbreviations})\.', r'\1<ABBREV>', text, flags=re.IGNORECASE)
        
        # Split on sentence-ending punctuation followed by whitespace and capital letter or end
        sentence_pattern = r'([.!?]+)\s+(?=[A-Z]|$)'
        parts = re.split(sentence_pattern, protected_text)
        
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i]
            if i + 1 < len(parts):
                sentence += parts[i + 1]  # Add the punctuation back
            
            # Restore abbreviations
            sentence = sentence.replace('<ABBREV>', '.')
            sentence = sentence.strip()
            
            if sentence:
                sentences.append(sentence)
        
        # Handle the last part if it doesn't end with punctuation
        if len(parts) % 2 == 1:
            last_part = parts[-1].replace('<ABBREV>', '.').strip()
            if last_part:
                sentences.append(last_part)
        
        return sentences if sentences else [text.strip()]
    
    def _write_speaker_formatted_text(self, result: Dict, file):
        """
        Write transcript in a speaker-formatted text format.
        Each sentence gets its own paragraph with speaker identification.
        """
        if not result.get('segments'):
            text = result.get('text', '').strip()
            if text:
                sentences = self._split_into_sentences(text)
                for sentence in sentences:
                    file.write(f"Unknown: {sentence}\n\n")
            return
        
        for segment in result['segments']:
            speaker = segment.get('speaker', 'Unknown')
            text = segment['text'].strip()
            
            if text:
                # Split the segment text into sentences
                sentences = self._split_into_sentences(text)
                
                for sentence in sentences:
                    if sentence.strip():
                        file.write(f"{speaker}: {sentence.strip()}\n\n")
        
        # Remove the extra newline at the end
        file.seek(file.tell() - 1)
        file.truncate()
    
    def _format_timestamp(self, seconds: float, srt: bool = True) -> str:
        """Format timestamp for SRT/VTT files."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        if srt:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def transcribe_file(self, input_path: Path, output_dir: Optional[Path] = None, 
                       format: str = "txt", language: Optional[str] = None,
                       preprocess: bool = True, enable_diarization: Optional[bool] = None) -> Path:
        """
        Complete transcription workflow for a single file.
        
        Args:
            input_path: Input audio file path
            output_dir: Output directory (default: same as input)
            format: Output format
            language: Language code
            preprocess: Whether to preprocess audio
            enable_diarization: Override diarization setting for this file
            
        Returns:
            Path to transcript file
        """
        if output_dir is None:
            output_dir = input_path.parent
        
        output_dir = Path(output_dir)
        suffix = "_speakers" if (enable_diarization if enable_diarization is not None else self.enable_diarization) else ""
        output_file = output_dir / f"{input_path.stem}{suffix}.{format}"
        
        # Temporarily override diarization setting if specified
        original_diarization = self.enable_diarization
        if enable_diarization is not None:
            self.enable_diarization = enable_diarization and PYANNOTE_AVAILABLE
        
        try:
            # Preprocess if needed
            if preprocess and PYDUB_AVAILABLE:
                processed_path = self.preprocess_audio(input_path)
                transcribe_path = processed_path
            else:
                transcribe_path = input_path
            
            # Transcribe with speaker diarization
            result = self.transcribe_audio(transcribe_path, language)
            
            # Save transcript
            self.save_transcript(result, output_file, format)
            
            # Clean up processed file if it was created
            if preprocess and transcribe_path != input_path and transcribe_path.exists():
                transcribe_path.unlink()
                print("🧹 Cleaned up temporary processed file")
        
        finally:
            # Restore original diarization setting
            self.enable_diarization = original_diarization
        
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe audio files to text using Whisper with speaker identification',
        epilog='Supported formats: MP3, WAV, M4A, FLAC, OGG, AAC, WMA\n'
               'Speaker identification helps separate different speakers in conversations.'
    )
    
    parser.add_argument('input', help='Input audio file or directory')
    parser.add_argument('-o', '--output', help='Output directory (default: same as input)')
    parser.add_argument('-f', '--format', choices=['txt', 'srt', 'vtt', 'json'], 
                       default='txt', help='Output format (default: txt)')
    parser.add_argument('-m', '--model', choices=['tiny', 'base', 'small', 'medium', 'large'],
                       default='base', help='Whisper model size (default: base)')
    parser.add_argument('-l', '--language', help='Language code (e.g., en, zh, es)')
    parser.add_argument('--no-preprocess', action='store_true',
                       help='Skip audio preprocessing')
    parser.add_argument('--no-diarization', action='store_true',
                       help='Disable speaker diarization (identification)')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto',
                       help='Device to use (default: auto)')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)
    
    # Initialize transcriber
    enable_diarization = not args.no_diarization
    transcriber = AudioTranscriber(
        model_size=args.model, 
        device=args.device,
        enable_diarization=enable_diarization
    )
    
    # Process files
    if input_path.is_file():
        # Single file
        try:
            output_file = transcriber.transcribe_file(
                input_path,
                Path(args.output) if args.output else None,
                args.format,
                args.language,
                not args.no_preprocess,
                enable_diarization
            )
            print(f"🎉 Transcription complete: {output_file}")
            
        except Exception as e:
            print(f"❌ Error processing {input_path}: {e}")
            sys.exit(1)
    
    elif input_path.is_dir():
        # Directory
        audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}
        audio_files = [f for f in input_path.iterdir() 
                      if f.suffix.lower() in audio_extensions]
        
        if not audio_files:
            print(f"❌ No audio files found in: {input_path}")
            sys.exit(1)
        
        print(f"📁 Found {len(audio_files)} audio file(s)")
        
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n[{i}/{len(audio_files)}]")
            try:
                output_file = transcriber.transcribe_file(
                    audio_file,
                    Path(args.output) if args.output else None,
                    args.format,
                    args.language,
                    not args.no_preprocess,
                    enable_diarization
                )
                print(f"✅ Completed: {output_file}")
                
            except Exception as e:
                print(f"❌ Error processing {audio_file}: {e}")
                continue
        
        print(f"\n🎉 Batch transcription complete!")
    
    else:
        print(f"❌ Invalid input path: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()