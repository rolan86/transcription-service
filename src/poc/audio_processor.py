"""
Audio processing utilities for POC transcription service.
Handles audio extraction from video files and audio preprocessing.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import ffmpeg
from pydub import AudioSegment


class AudioProcessor:
    """Handles audio extraction and preprocessing."""
    
    TEMP_AUDIO_FORMAT = 'wav'
    SAMPLE_RATE = 16000  # Standard for speech recognition
    CHANNELS = 1  # Mono for better transcription
    
    def __init__(self):
        self.temp_files = []
    
    def __del__(self):
        """Cleanup temporary files."""
        self.cleanup_temp_files()
    
    def cleanup_temp_files(self):
        """Remove all temporary files created during processing."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Could not remove temp file {temp_file}: {e}")
        self.temp_files.clear()
    
    def extract_audio_from_video(self, video_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Extract audio from MP4 video file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Tuple of (success, message, temp_audio_path)
        """
        try:
            # Create temporary file for extracted audio
            temp_fd, temp_audio_path = tempfile.mkstemp(suffix=f'.{self.TEMP_AUDIO_FORMAT}')
            os.close(temp_fd)  # Close file descriptor, keep the path
            self.temp_files.append(temp_audio_path)
            
            # Extract audio using ffmpeg
            (
                ffmpeg
                .input(video_path)
                .output(
                    temp_audio_path,
                    acodec='pcm_s16le',  # Uncompressed WAV
                    ac=self.CHANNELS,    # Mono
                    ar=self.SAMPLE_RATE  # 16kHz sample rate
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Verify the extracted file exists and has content
            if not os.path.exists(temp_audio_path) or os.path.getsize(temp_audio_path) == 0:
                return False, "Audio extraction failed - no output generated", None
            
            return True, f"Audio extracted successfully to {temp_audio_path}", temp_audio_path
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
            return False, error_msg, None
        except Exception as e:
            return False, f"Unexpected error during audio extraction: {str(e)}", None
    
    def preprocess_audio(self, audio_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Preprocess audio file for better transcription.
        Converts to standard format and applies basic filtering.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Tuple of (success, message, processed_audio_path)
        """
        try:
            # Load audio file
            audio = AudioSegment.from_file(audio_path)
            
            # Convert to mono
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Set sample rate
            if audio.frame_rate != self.SAMPLE_RATE:
                audio = audio.set_frame_rate(self.SAMPLE_RATE)
            
            # Normalize volume (basic preprocessing)
            audio = audio.normalize()
            
            # Create temporary file for processed audio
            temp_fd, temp_processed_path = tempfile.mkstemp(suffix=f'.{self.TEMP_AUDIO_FORMAT}')
            os.close(temp_fd)
            self.temp_files.append(temp_processed_path)
            
            # Export processed audio
            audio.export(temp_processed_path, format=self.TEMP_AUDIO_FORMAT)
            
            return True, f"Audio preprocessed successfully", temp_processed_path
            
        except Exception as e:
            return False, f"Audio preprocessing failed: {str(e)}", None
    
    def process_file(self, file_path: str, file_type: str) -> Tuple[bool, str, Optional[str]]:
        """
        Process file based on its type (audio or video).
        
        Args:
            file_path: Path to the input file
            file_type: Type of file ('audio' or 'video')
            
        Returns:
            Tuple of (success, message, processed_audio_path)
        """
        if file_type == 'video':
            # Extract audio from video
            success, message, audio_path = self.extract_audio_from_video(file_path)
            if not success:
                return success, message, audio_path
            
            # Preprocess the extracted audio
            return self.preprocess_audio(audio_path)
            
        elif file_type == 'audio':
            # Direct audio preprocessing
            return self.preprocess_audio(file_path)
            
        else:
            return False, f"Unsupported file type: {file_type}", None
    
    def get_audio_info(self, audio_path: str) -> dict:
        """
        Get information about audio file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary with audio information
        """
        try:
            audio = AudioSegment.from_file(audio_path)
            duration_seconds = len(audio) / 1000.0
            
            return {
                'duration_seconds': duration_seconds,
                'duration_formatted': f"{int(duration_seconds // 60):02d}:{int(duration_seconds % 60):02d}",
                'channels': audio.channels,
                'frame_rate': audio.frame_rate,
                'sample_width': audio.sample_width,
                'file_size_mb': round(os.path.getsize(audio_path) / (1024 * 1024), 2)
            }
        except Exception as e:
            return {'error': f"Could not analyze audio: {str(e)}"}