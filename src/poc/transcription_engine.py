"""
Transcription engine for POC using OpenAI Whisper.
Handles speech-to-text conversion with basic confidence tracking.
"""

import whisper
import time
import os
from typing import Dict, Optional, Tuple
import torch


class TranscriptionEngine:
    """Handles speech-to-text transcription using Whisper."""
    
    def __init__(self, model_size: str = "base", whisper_config: Optional[Dict] = None):
        """
        Initialize transcription engine.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            whisper_config: Optional Whisper-specific configuration
        """
        self.model_size = model_size
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.whisper_config = whisper_config or {}
        
        # Set Whisper environment variables if configured
        self._configure_whisper_environment()
    
    def _configure_whisper_environment(self):
        """Configure Whisper environment variables based on config."""
        env_mapping = {
            'cache_dir': 'WHISPER_CACHE_DIR',
            'download_root': 'WHISPER_DOWNLOAD_ROOT',
            'download_timeout': 'WHISPER_DOWNLOAD_TIMEOUT',
            'no_progress': 'WHISPER_NO_PROGRESS'
        }
        
        for config_key, env_var in env_mapping.items():
            if config_key in self.whisper_config and self.whisper_config[config_key] is not None:
                value = self.whisper_config[config_key]
                
                # Convert boolean to string for environment variables
                if isinstance(value, bool):
                    value = 'true' if value else 'false'
                
                os.environ[env_var] = str(value)
        
    def load_model(self) -> Tuple[bool, str]:
        """
        Load Whisper model.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"Loading Whisper model '{self.model_size}' on {self.device}...")
            start_time = time.time()
            
            self.model = whisper.load_model(self.model_size, device=self.device)
            
            load_time = time.time() - start_time
            return True, f"Model loaded successfully in {load_time:.2f} seconds"
            
        except Exception as e:
            return False, f"Failed to load model: {str(e)}"
    
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None,
                         initial_prompt: Optional[str] = None) -> Dict:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to the audio file
            language: Language code (e.g., 'en', 'es') or None for auto-detection
            initial_prompt: Optional prompt to condition the model with custom vocabulary

        Returns:
            Dictionary with transcription results
        """
        if self.model is None:
            success, message = self.load_model()
            if not success:
                return {
                    'success': False,
                    'error': message,
                    'text': None,
                    'segments': None,
                    'language': None,
                    'processing_time': 0
                }

        try:
            print(f"Transcribing audio: {audio_path}")
            if initial_prompt:
                print(f"Using custom vocabulary prompt")
            start_time = time.time()

            # Build transcribe options
            transcribe_options = {
                'language': language,
                'verbose': False,  # Reduce console output
                'word_timestamps': True,  # Enable word-level timestamps
            }

            # Add initial prompt if provided (for custom vocabulary)
            if initial_prompt:
                transcribe_options['initial_prompt'] = initial_prompt

            # Transcribe with Whisper
            result = self.model.transcribe(audio_path, **transcribe_options)
            
            processing_time = time.time() - start_time
            
            # Extract text and segments
            text = result.get('text', '').strip()
            segments = result.get('segments', [])
            detected_language = result.get('language', 'unknown')
            
            # Calculate basic confidence score (average of segment probabilities)
            avg_confidence = 0.0
            if segments:
                confidences = [seg.get('avg_logprob', 0) for seg in segments]
                # Convert log probabilities to more readable confidence scores
                avg_confidence = sum(confidences) / len(confidences)
                # Normalize to 0-1 range (rough approximation)
                avg_confidence = max(0, min(1, (avg_confidence + 1) / 1))
            
            return {
                'success': True,
                'text': text,
                'segments': segments,
                'language': detected_language,
                'confidence': round(avg_confidence, 3),
                'processing_time': round(processing_time, 2),
                'word_count': len(text.split()) if text else 0,
                'segment_count': len(segments)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Transcription failed: {str(e)}",
                'text': None,
                'segments': None,
                'language': None,
                'processing_time': 0
            }
    
    def format_transcript(self, result: Dict, include_timestamps: bool = False) -> str:
        """
        Format transcription result for display.
        
        Args:
            result: Transcription result dictionary
            include_timestamps: Whether to include segment timestamps
            
        Returns:
            Formatted transcript string
        """
        if not result['success']:
            return f"Transcription failed: {result.get('error', 'Unknown error')}"
        
        text = result['text']
        if not text:
            return "No speech detected in audio."
        
        if not include_timestamps:
            return text
        
        # Format with timestamps
        formatted_lines = []
        segments = result.get('segments', [])
        
        for segment in segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            segment_text = segment.get('text', '').strip()
            
            if segment_text:
                timestamp = f"[{self._format_time(start_time)} -> {self._format_time(end_time)}]"
                formatted_lines.append(f"{timestamp} {segment_text}")
        
        return '\n'.join(formatted_lines) if formatted_lines else text
    
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_model_info(self) -> Dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_size': self.model_size,
            'device': self.device,
            'loaded': self.model is not None,
            'gpu_available': torch.cuda.is_available(),
            'gpu_device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }