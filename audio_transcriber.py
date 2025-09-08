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
import shutil
import glob

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
    
    def get_file_size_mb(self, file_path: Path) -> float:
        """
        Get file size in MB.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in MB
        """
        return file_path.stat().st_size / (1024 * 1024)
    
    def split_large_audio(self, audio_path: Path, segment_minutes: int = 5, max_size_mb: int = 10) -> List[Path]:
        """
        Split large audio files into smaller segments.
        
        Args:
            audio_path: Input audio file path
            segment_minutes: Length of each segment in minutes
            max_size_mb: Maximum file size in MB before splitting
            
        Returns:
            List of segment file paths (original file if not split)
        """
        if not PYDUB_AVAILABLE:
            print("⚠️  pydub not available. Cannot split large files.")
            return [audio_path]
        
        file_size_mb = self.get_file_size_mb(audio_path)
        
        if file_size_mb <= max_size_mb:
            print(f"📊 File size: {file_size_mb:.1f}MB (no splitting needed)")
            return [audio_path]
        
        print(f"📊 File size: {file_size_mb:.1f}MB (splitting into {segment_minutes}-minute segments)")
        
        try:
            # Load audio
            audio = AudioSegment.from_file(str(audio_path))
            
            # Calculate segment length in milliseconds
            segment_ms = segment_minutes * 60 * 1000
            
            # Create segments directory
            segments_dir = audio_path.parent / f"{audio_path.stem}_segments"
            segments_dir.mkdir(exist_ok=True)
            
            segments = []
            total_segments = len(audio) // segment_ms + (1 if len(audio) % segment_ms else 0)
            
            print(f"🔪 Splitting into {total_segments} segments...")
            
            for i in range(0, len(audio), segment_ms):
                segment = audio[i:i + segment_ms]
                segment_num = (i // segment_ms) + 1
                segment_filename = f"{audio_path.stem}_part{segment_num:03d}{audio_path.suffix}"
                segment_path = segments_dir / segment_filename
                
                # Export segment
                segment.export(str(segment_path), format=audio_path.suffix[1:])
                segments.append(segment_path)
                
                print(f"   📁 Created: {segment_filename} ({len(segment)/1000:.1f}s)")
            
            print(f"✅ Audio split into {len(segments)} segments in: {segments_dir}")
            return segments
            
        except Exception as e:
            print(f"❌ Failed to split audio: {e}")
            return [audio_path]
    
    def merge_transcripts(self, transcript_paths: List[Path], original_filename: str, 
                         output_dir: Path, format: str = "txt") -> Path:
        """
        Merge multiple transcript files from audio segments.
        
        Args:
            transcript_paths: List of transcript file paths
            original_filename: Original audio filename (without extension)
            output_dir: Output directory
            format: Output format
            
        Returns:
            Path to merged transcript file
        """
        merged_filename = f"{original_filename}_merged.{format}"
        merged_path = output_dir / merged_filename
        
        print(f"📋 Merging {len(transcript_paths)} transcripts...")
        
        if format == "txt":
            with open(merged_path, 'w', encoding='utf-8') as merged_file:
                for i, transcript_path in enumerate(transcript_paths):
                    if transcript_path.exists():
                        with open(transcript_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                if i > 0:
                                    merged_file.write("\n\n")
                                merged_file.write(content)
                            
        elif format in ["srt", "vtt"]:
            # For subtitle formats, we need to adjust timestamps
            self._merge_subtitle_files(transcript_paths, merged_path, format)
            
        elif format == "json":
            # Merge JSON transcripts
            self._merge_json_files(transcript_paths, merged_path)
        
        print(f"✅ Merged transcript saved: {merged_path}")
        return merged_path
    
    def _merge_subtitle_files(self, transcript_paths: List[Path], output_path: Path, format: str):
        """Merge SRT or VTT files with proper timestamp adjustment."""
        segment_counter = 1
        total_offset = 0.0
        
        with open(output_path, 'w', encoding='utf-8') as merged_file:
            if format == "vtt":
                merged_file.write("WEBVTT\n\n")
            
            for segment_idx, transcript_path in enumerate(transcript_paths):
                if not transcript_path.exists():
                    continue
                
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                i = 0
                if format == "vtt" and lines and lines[0].startswith("WEBVTT"):
                    i = 2  # Skip WEBVTT header
                
                while i < len(lines):
                    line = lines[i].strip()
                    
                    if not line:
                        i += 1
                        continue
                    
                    if format == "srt" and line.isdigit():
                        # SRT subtitle number
                        merged_file.write(f"{segment_counter}\n")
                        segment_counter += 1
                        i += 1
                    elif "-->" in line:
                        # Timestamp line - adjust timestamps
                        adjusted_line = self._adjust_timestamps(line, total_offset)
                        merged_file.write(adjusted_line + "\n")
                        i += 1
                    else:
                        # Text line
                        merged_file.write(line + "\n")
                        i += 1
                
                # Update offset for next segment (5 minutes in seconds)
                total_offset += 5 * 60
                merged_file.write("\n")
    
    def _merge_json_files(self, transcript_paths: List[Path], output_path: Path):
        """Merge JSON transcript files."""
        merged_result = {
            "text": "",
            "segments": [],
            "language": None
        }
        
        total_offset = 0.0
        
        for transcript_path in transcript_paths:
            if not transcript_path.exists():
                continue
            
            with open(transcript_path, 'r', encoding='utf-8') as f:
                segment_result = json.load(f)
            
            # Append text
            if merged_result["text"]:
                merged_result["text"] += " "
            merged_result["text"] += segment_result.get("text", "")
            
            # Adjust and append segments
            for segment in segment_result.get("segments", []):
                adjusted_segment = segment.copy()
                adjusted_segment["start"] += total_offset
                adjusted_segment["end"] += total_offset
                merged_result["segments"].append(adjusted_segment)
            
            # Set language from first segment
            if merged_result["language"] is None:
                merged_result["language"] = segment_result.get("language")
            
            total_offset += 5 * 60  # 5 minutes
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_result, f, indent=2, ensure_ascii=False)
    
    def _adjust_timestamps(self, timestamp_line: str, offset_seconds: float) -> str:
        """Adjust timestamps in SRT/VTT format by adding offset."""
        # Parse timestamps like "00:01:23,456 --> 00:01:25,789"
        parts = timestamp_line.split(" --> ")
        if len(parts) != 2:
            return timestamp_line
        
        start_ts = self._parse_timestamp(parts[0].strip())
        end_ts = self._parse_timestamp(parts[1].strip())
        
        if start_ts is None or end_ts is None:
            return timestamp_line
        
        # Add offset
        start_ts += offset_seconds
        end_ts += offset_seconds
        
        # Format back to timestamp string
        start_formatted = self._format_timestamp(start_ts, srt="," in parts[0])
        end_formatted = self._format_timestamp(end_ts, srt="," in parts[1])
        
        return f"{start_formatted} --> {end_formatted}"
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[float]:
        """Parse SRT/VTT timestamp to seconds."""
        try:
            # Handle both SRT (comma) and VTT (dot) formats
            timestamp_str = timestamp_str.replace(',', '.')
            
            parts = timestamp_str.split(':')
            if len(parts) != 3:
                return None
            
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            return hours * 3600 + minutes * 60 + seconds
        except:
            return None

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
        Assign generic speakers based on pauses, creating natural segments for better readability.
        When speaker diarization is disabled, this creates paragraph-like breaks at speaking pauses.
        """
        enhanced_segments = []
        current_speaker = 'Speaker'
        last_end = 0
        segment_group = []
        
        # Group segments by pauses for better readability
        for i, segment in enumerate(transcription['segments']):
            pause_duration = segment['start'] - last_end if i > 0 else 0
            
            # Detect natural speaking breaks (pauses longer than 1.5 seconds)
            is_new_paragraph = (pause_duration > 1.5 and i > 0)
            
            # Also break on sentence endings followed by pauses
            if i > 0 and pause_duration > 0.8:
                prev_text = transcription['segments'][i-1]['text'].strip()
                if any(prev_text.endswith(punct) for punct in ['.', '!', '?', '。', '！', '？']):
                    is_new_paragraph = True
            
            if is_new_paragraph and segment_group:
                # Create a merged segment from the group
                merged_segment = self._merge_segment_group(segment_group, current_speaker)
                enhanced_segments.append(merged_segment)
                segment_group = []
            
            # Add current segment to group
            enhanced_segment = segment.copy()
            enhanced_segment['speaker'] = current_speaker
            segment_group.append(enhanced_segment)
            
            last_end = segment['end']
        
        # Add the last group
        if segment_group:
            merged_segment = self._merge_segment_group(segment_group, current_speaker)
            enhanced_segments.append(merged_segment)
        
        result = transcription.copy()
        result['segments'] = enhanced_segments
        return result
    
    def _merge_segment_group(self, segments: List[Dict], speaker: str) -> Dict:
        """
        Merge a group of segments into a single paragraph-like segment.
        """
        if not segments:
            return {}
        
        if len(segments) == 1:
            return segments[0]
        
        # Merge the segments
        merged_text = ' '.join(seg['text'].strip() for seg in segments if seg['text'].strip())
        
        return {
            'start': segments[0]['start'],
            'end': segments[-1]['end'], 
            'text': merged_text,
            'speaker': speaker
        }
    
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
                       preprocess: bool = True, enable_diarization: Optional[bool] = None,
                       max_size_mb: int = 10, segment_minutes: int = 5) -> Path:
        """
        Complete transcription workflow for a single file with automatic splitting for large files.
        
        Args:
            input_path: Input audio file path
            output_dir: Output directory (default: same as input)
            format: Output format
            language: Language code
            preprocess: Whether to preprocess audio
            enable_diarization: Override diarization setting for this file
            max_size_mb: Maximum file size in MB before splitting
            segment_minutes: Length of each segment in minutes when splitting
            
        Returns:
            Path to transcript file
        """
        if output_dir is None:
            output_dir = input_path.parent
        
        output_dir = Path(output_dir)
        suffix = "_speakers" if (enable_diarization if enable_diarization is not None else self.enable_diarization) else ""
        
        # Temporarily override diarization setting if specified
        original_diarization = self.enable_diarization
        if enable_diarization is not None:
            self.enable_diarization = enable_diarization and PYANNOTE_AVAILABLE
        
        try:
            # Step 1: Check if file needs splitting
            segments = self.split_large_audio(input_path, segment_minutes, max_size_mb)
            
            if len(segments) == 1:
                # Single file, use original workflow
                output_file = output_dir / f"{input_path.stem}{suffix}.{format}"
                
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
                
                return output_file
            
            else:
                # Multiple segments, transcribe each and merge
                print(f"🔄 Transcribing {len(segments)} segments...")
                
                transcript_paths = []
                cleanup_paths = []
                
                for i, segment_path in enumerate(segments, 1):
                    print(f"\n[{i}/{len(segments)}] Processing: {segment_path.name}")
                    
                    # Preprocess if needed
                    if preprocess and PYDUB_AVAILABLE:
                        processed_path = self.preprocess_audio(segment_path)
                        transcribe_path = processed_path
                        if processed_path != segment_path:
                            cleanup_paths.append(processed_path)
                    else:
                        transcribe_path = segment_path
                    
                    # Transcribe segment
                    result = self.transcribe_audio(transcribe_path, language)
                    
                    # Save segment transcript
                    segment_output = segment_path.parent / f"{segment_path.stem}{suffix}.{format}"
                    self.save_transcript(result, segment_output, format)
                    transcript_paths.append(segment_output)
                
                # Merge all transcripts
                merged_output = self.merge_transcripts(
                    transcript_paths, 
                    input_path.stem, 
                    output_dir, 
                    format
                )
                
                # Clean up temporary files
                for cleanup_path in cleanup_paths:
                    if cleanup_path.exists():
                        cleanup_path.unlink()
                
                # Optionally clean up segment files
                segments_dir = segments[0].parent
                print(f"🧹 Segment files available in: {segments_dir}")
                print(f"🧹 Individual transcripts available in: {segments_dir}")
                
                return merged_output
        
        finally:
            # Restore original diarization setting
            self.enable_diarization = original_diarization
    
    def list_audio_files(self, directory: Path = None) -> List[Path]:
        """
        List all audio files in the specified directory.
        
        Args:
            directory: Directory to search (default: downloads)
            
        Returns:
            List of audio file paths
        """
        if directory is None:
            directory = Path("downloads")
        
        if not directory.exists():
            return []
        
        # Supported audio extensions
        audio_extensions = ['.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.wma']
        audio_files = []
        
        for ext in audio_extensions:
            pattern = str(directory / f"*{ext}")
            audio_files.extend([Path(f) for f in glob.glob(pattern, recursive=False)])
            # Also check uppercase extensions
            pattern = str(directory / f"*{ext.upper()}")
            audio_files.extend([Path(f) for f in glob.glob(pattern, recursive=False)])
        
        # Remove duplicates and sort
        audio_files = list(set(audio_files))
        audio_files.sort(key=lambda x: x.name.lower())
        
        return audio_files
    
    def display_file_menu(self, audio_files: List[Path]) -> int:
        """
        Display interactive menu for file selection.
        
        Args:
            audio_files: List of audio files
            
        Returns:
            Selected file index (0-based) or -1 for exit
        """
        print("\n📁 在 downloads 目录下找到以下音频文件:")
        print("=" * 60)
        
        for i, file_path in enumerate(audio_files, 1):
            file_size = self.get_file_size_mb(file_path)
            duration_info = self._get_duration_info(file_path)
            
            print(f"{i:2d}. {file_path.name}")
            print(f"    大小: {file_size:.1f} MB{duration_info}")
            print(f"    路径: {file_path}")
            print()
        
        print("0. 退出")
        print("=" * 60)
        
        while True:
            try:
                choice = input("请选择要转录的文件 (输入编号): ").strip()
                
                if choice == '0':
                    return -1
                
                index = int(choice) - 1
                if 0 <= index < len(audio_files):
                    return index
                else:
                    print(f"❌ 请输入有效编号 (0-{len(audio_files)})")
                    
            except ValueError:
                print("❌ 请输入数字编号")
            except KeyboardInterrupt:
                print("\n\n👋 退出程序")
                return -1
    
    def _get_duration_info(self, file_path: Path) -> str:
        """
        Get audio file duration information.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Duration info string
        """
        if not PYDUB_AVAILABLE:
            return ""
        
        try:
            audio = AudioSegment.from_file(str(file_path))
            duration_seconds = len(audio) / 1000
            
            if duration_seconds < 60:
                return f", 时长: {duration_seconds:.0f}秒"
            elif duration_seconds < 3600:
                minutes = duration_seconds / 60
                return f", 时长: {minutes:.1f}分钟"
            else:
                hours = duration_seconds / 3600
                return f", 时长: {hours:.1f}小时"
                
        except Exception:
            return ""
    
    def select_audio_file_interactively(self, directory: Path = None) -> Optional[Path]:
        """
        Interactive audio file selection from downloads directory.
        
        Args:
            directory: Directory to search (default: downloads)
            
        Returns:
            Selected file path or None if cancelled
        """
        if directory is None:
            directory = Path("downloads")
        
        # Check if downloads directory exists
        if not directory.exists():
            print(f"❌ 目录不存在: {directory}")
            print(f"💡 请先使用 podcast_downloader.py 下载一些音频文件")
            return None
        
        # List audio files
        audio_files = self.list_audio_files(directory)
        
        if not audio_files:
            print(f"❌ 在 {directory} 目录下未找到音频文件")
            print(f"💡 支持的格式: MP3, M4A, WAV, FLAC, OGG, AAC, WMA")
            print(f"💡 请先使用 podcast_downloader.py 下载一些音频文件")
            return None
        
        # Display menu and get selection
        selected_index = self.display_file_menu(audio_files)
        
        if selected_index == -1:
            return None
        
        selected_file = audio_files[selected_index]
        print(f"\n✅ 已选择: {selected_file.name}")
        return selected_file


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe audio files to text using Whisper with speaker identification',
        epilog='Supported formats: MP3, M4A, WAV, FLAC, OGG, AAC, WMA\n'
               'Speaker identification helps separate different speakers in conversations.'
    )
    
    parser.add_argument('input', nargs='?', help='Input audio file or directory')
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
    parser.add_argument('--max-size', type=int, default=10,
                       help='Maximum file size in MB before splitting (default: 10)')
    parser.add_argument('--segment-minutes', type=int, default=5,
                       help='Length of each segment in minutes when splitting (default: 5)')
    
    args = parser.parse_args()
    
    # Initialize transcriber
    enable_diarization = not args.no_diarization
    transcriber = AudioTranscriber(
        model_size=args.model, 
        device=args.device,
        enable_diarization=enable_diarization
    )
    
    # Determine input file
    if args.input:
        # File provided via command line
        input_path = Path(args.input)
        
        if not input_path.exists():
            print(f"❌ Input file not found: {input_path}")
            sys.exit(1)
    else:
        # Interactive mode - select from downloads directory
        print("🎙️ 音频转录工具")
        print("支持格式: MP3, M4A, WAV, FLAC, OGG, AAC, WMA")
        print("支持说话人识别功能，可区分对话中的不同说话者")
        
        selected_file = transcriber.select_audio_file_interactively()
        if not selected_file:
            print("\n👋 未选择文件，程序退出")
            sys.exit(0)
        
        input_path = selected_file
    
    # Process files
    if input_path.is_file():
        # Single file
        try:
            print(f"\n🎤 开始转录: {input_path.name}")
            output_file = transcriber.transcribe_file(
                input_path,
                Path(args.output) if args.output else None,
                args.format,
                args.language,
                not args.no_preprocess,
                enable_diarization,
                args.max_size,
                args.segment_minutes
            )
            print(f"\n🎉 转录完成: {output_file}")
            
        except Exception as e:
            print(f"❌ Error processing {input_path}: {e}")
            sys.exit(1)
    
    elif input_path.is_dir():
        # Directory processing
        audio_extensions = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.wma'}
        audio_files = [f for f in input_path.iterdir() 
                      if f.suffix.lower() in audio_extensions]
        
        if not audio_files:
            print(f"❌ No audio files found in: {input_path}")
            sys.exit(1)
        
        print(f"📁 Found {len(audio_files)} audio file(s)")
        
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n[{i}/{len(audio_files)}] Processing: {audio_file.name}")
            try:
                output_file = transcriber.transcribe_file(
                    audio_file,
                    Path(args.output) if args.output else None,
                    args.format,
                    args.language,
                    not args.no_preprocess,
                    enable_diarization,
                    args.max_size,
                    args.segment_minutes
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