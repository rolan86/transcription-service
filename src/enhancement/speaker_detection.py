"""
Speaker Detection and Diarization module for Phase 3A enhancements.
Provides speaker identification and separation using pyannote.audio.
"""

import os
import tempfile
import warnings
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

try:
    from pyannote.audio import Pipeline
    from pyannote.core import Annotation, Segment
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    Pipeline = None
    Annotation = None
    Segment = None


class SpeakerDetector:
    """Handles speaker detection and diarization using pyannote.audio."""
    
    def __init__(self, enable_huggingface_token: bool = False):
        """
        Initialize speaker detector.
        
        Args:
            enable_huggingface_token: Whether to use HuggingFace token for better models
        """
        self.pipeline = None
        self.enabled = PYANNOTE_AVAILABLE
        self.huggingface_token = enable_huggingface_token
        
        if not PYANNOTE_AVAILABLE:
            warnings.warn(
                "pyannote.audio not available. Speaker detection disabled. "
                "Install with: pip install pyannote.audio"
            )
    
    def load_pipeline(self) -> Tuple[bool, str]:
        """
        Load the speaker diarization pipeline.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.enabled:
            return False, "pyannote.audio not available"
        
        try:
            # Use the latest speaker diarization pipeline
            model_name = "pyannote/speaker-diarization-3.1"
            
            # Check for HuggingFace token
            hf_token = None
            if self.huggingface_token:
                hf_token = os.getenv('HUGGINGFACE_TOKEN')
                if not hf_token:
                    print("⚠️  No HUGGINGFACE_TOKEN found. Using public model (may have limitations)")
            
            print(f"Loading speaker diarization model: {model_name}")
            self.pipeline = Pipeline.from_pretrained(
                model_name,
                use_auth_token=hf_token
            )
            
            return True, f"Speaker diarization pipeline loaded successfully"
            
        except Exception as e:
            error_msg = f"Failed to load speaker diarization pipeline: {str(e)}"
            if "authentication" in str(e).lower() or "token" in str(e).lower():
                error_msg += "\n💡 Tip: Set HUGGINGFACE_TOKEN environment variable for better models"
            return False, error_msg
    
    def detect_speakers(self, audio_path: str, num_speakers: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform speaker diarization on audio file.
        
        Args:
            audio_path: Path to audio file
            num_speakers: Optional hint for number of speakers
            
        Returns:
            Dictionary with speaker detection results
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Speaker detection not available',
                'speakers': [],
                'speaker_segments': []
            }
        
        if self.pipeline is None:
            success, message = self.load_pipeline()
            if not success:
                return {
                    'success': False,
                    'error': message,
                    'speakers': [],
                    'speaker_segments': []
                }
        
        try:
            print(f"🎭 Detecting speakers in: {Path(audio_path).name}")
            
            # Apply the pipeline
            diarization_kwargs = {}
            if num_speakers:
                diarization_kwargs['num_speakers'] = num_speakers
            
            diarization = self.pipeline(audio_path, **diarization_kwargs)
            
            # Process results
            speakers = list(diarization.labels())
            speaker_segments = []
            
            for segment, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segments.append({
                    'start': float(segment.start),
                    'end': float(segment.end),
                    'speaker': speaker,
                    'duration': float(segment.end - segment.start)
                })
            
            # Calculate speaker statistics
            speaker_stats = {}
            for segment in speaker_segments:
                speaker = segment['speaker']
                if speaker not in speaker_stats:
                    speaker_stats[speaker] = {
                        'total_duration': 0.0,
                        'segment_count': 0
                    }
                speaker_stats[speaker]['total_duration'] += segment['duration']
                speaker_stats[speaker]['segment_count'] += 1
            
            # Sort speakers by total speaking time
            sorted_speakers = sorted(
                speaker_stats.items(),
                key=lambda x: x[1]['total_duration'],
                reverse=True
            )
            
            return {
                'success': True,
                'speakers': speakers,
                'speaker_count': len(speakers),
                'speaker_segments': speaker_segments,
                'speaker_stats': dict(speaker_stats),
                'sorted_speakers': sorted_speakers,
                'total_segments': len(speaker_segments)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Speaker detection failed: {str(e)}",
                'speakers': [],
                'speaker_segments': []
            }
    
    def merge_with_transcription(self, transcription_segments: List[Dict], 
                               speaker_segments: List[Dict]) -> List[Dict]:
        """
        Merge speaker information with transcription segments.
        
        Args:
            transcription_segments: Segments from Whisper transcription
            speaker_segments: Segments from speaker diarization
            
        Returns:
            Merged segments with speaker information
        """
        if not speaker_segments:
            return transcription_segments
        
        merged_segments = []
        
        for trans_seg in transcription_segments:
            trans_start = trans_seg.get('start', 0)
            trans_end = trans_seg.get('end', trans_start)
            trans_mid = (trans_start + trans_end) / 2
            
            # Find the speaker segment that overlaps most with this transcription segment
            best_speaker = "UNKNOWN"
            best_overlap = 0
            
            for speaker_seg in speaker_segments:
                spk_start = speaker_seg['start']
                spk_end = speaker_seg['end']
                
                # Calculate overlap
                overlap_start = max(trans_start, spk_start)
                overlap_end = min(trans_end, spk_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = speaker_seg['speaker']
            
            # Add speaker information to transcription segment
            merged_segment = trans_seg.copy()
            merged_segment['speaker'] = best_speaker
            merged_segment['speaker_confidence'] = best_overlap / (trans_end - trans_start) if trans_end > trans_start else 0
            merged_segments.append(merged_segment)
        
        return merged_segments
    
    def format_speaker_output(self, segments: List[Dict], include_confidence: bool = False) -> str:
        """
        Format speaker-aware transcription for display.
        
        Args:
            segments: Merged segments with speaker information
            include_confidence: Whether to include speaker confidence
            
        Returns:
            Formatted text with speaker labels
        """
        if not segments:
            return "No segments available for speaker formatting."
        
        formatted_lines = []
        current_speaker = None
        
        for segment in segments:
            speaker = segment.get('speaker', 'UNKNOWN')
            text = segment.get('text', '').strip()
            start_time = segment.get('start', 0)
            
            if not text:
                continue
            
            # Add speaker label if changed
            if speaker != current_speaker:
                current_speaker = speaker
                speaker_label = f"\n[{speaker}]"
                if include_confidence:
                    confidence = segment.get('speaker_confidence', 0)
                    speaker_label += f" (confidence: {confidence:.1%})"
                formatted_lines.append(speaker_label)
            
            # Format timestamp
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            
            formatted_lines.append(f"{timestamp} {text}")
        
        return '\n'.join(formatted_lines)
    
    def get_speaker_summary(self, speaker_stats: Dict) -> str:
        """
        Generate a summary of speakers and their statistics.
        
        Args:
            speaker_stats: Speaker statistics from detection
            
        Returns:
            Formatted speaker summary
        """
        if not speaker_stats:
            return "No speaker statistics available."
        
        lines = ["Speaker Summary:", "=" * 50]
        
        # Sort by speaking time
        sorted_speakers = sorted(
            speaker_stats.items(),
            key=lambda x: x[1]['total_duration'],
            reverse=True
        )
        
        for i, (speaker, stats) in enumerate(sorted_speakers, 1):
            duration = stats['total_duration']
            segments = stats['segment_count']
            
            lines.append(
                f"{i}. {speaker}: {duration:.1f}s ({segments} segments)"
            )
        
        return '\n'.join(lines)


def is_speaker_detection_available() -> bool:
    """Check if speaker detection is available."""
    return PYANNOTE_AVAILABLE


def get_speaker_detection_info() -> Dict[str, Any]:
    """Get information about speaker detection capabilities."""
    return {
        'available': PYANNOTE_AVAILABLE,
        'library': 'pyannote.audio' if PYANNOTE_AVAILABLE else 'Not installed',
        'features': [
            'Speaker diarization',
            'Speaker identification',
            'Speaker statistics',
            'Integration with transcription'
        ] if PYANNOTE_AVAILABLE else [],
        'requirements': [
            'pyannote.audio>=3.1.0',
            'pyannote.pipeline>=3.0.1',
            'pytorch-lightning>=2.0.0'
        ]
    }