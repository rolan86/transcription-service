"""
Enhancement modules for Phase 3 features.

This package contains advanced features including:
- Speaker detection and diarization
- Audio preprocessing and enhancement
- Performance optimizations
- Enhanced metadata output
"""

from .speaker_detection import SpeakerDetector, is_speaker_detection_available, get_speaker_detection_info

__all__ = [
    'SpeakerDetector',
    'is_speaker_detection_available', 
    'get_speaker_detection_info'
]