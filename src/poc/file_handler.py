"""
File handling utilities for POC transcription service.
Supports format detection and validation for MP3, WAV, and MP4 files.
"""

import os
from pathlib import Path
from typing import Tuple, Optional


class FileHandler:
    """Handles file operations and format detection."""
    
    SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.flac'}
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mov', '.avi'}
    
    @classmethod
    def get_supported_formats(cls) -> set:
        """Return all supported file formats."""
        return cls.SUPPORTED_AUDIO_FORMATS | cls.SUPPORTED_VIDEO_FORMATS
    
    @staticmethod
    def validate_file(file_path: str, skip_size_check: bool = False, max_size_mb: int = 100) -> Tuple[bool, str]:
        """
        Validate if file exists and is supported.
        
        Args:
            file_path: Path to the file
            skip_size_check: Skip file size validation (for chunked processing)
            max_size_mb: Maximum file size in MB (configurable)
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"
        
        file_ext = Path(file_path).suffix.lower()
        supported_formats = FileHandler.get_supported_formats()
        
        if file_ext not in supported_formats:
            return False, f"Unsupported format: {file_ext}. Supported: {supported_formats}"
        
        # Check file size (basic validation)
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty"
        
        # Size limit check (can be skipped for chunked processing)
        if not skip_size_check:
            max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
            if file_size > max_size:
                return False, f"File too large: {file_size / (1024*1024):.1f}MB. Max: {max_size_mb}MB"
        
        return True, "File is valid"
    
    @staticmethod
    def detect_format(file_path: str) -> Optional[str]:
        """
        Detect file format based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Format type: 'audio' or 'video', None if unsupported
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in FileHandler.SUPPORTED_AUDIO_FORMATS:
            return 'audio'
        elif file_ext in FileHandler.SUPPORTED_VIDEO_FORMATS:
            return 'video'
        else:
            return None
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Get basic file information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        path = Path(file_path)
        file_size = os.path.getsize(file_path)
        
        return {
            'path': str(path.absolute()),
            'name': path.name,
            'extension': path.suffix.lower(),
            'size_bytes': file_size,
            'size_mb': round(file_size / (1024 * 1024), 2),
            'format_type': FileHandler.detect_format(file_path)
        }