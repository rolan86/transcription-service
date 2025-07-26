#!/usr/bin/env python3
"""
Test script for POC components
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from poc.file_handler import FileHandler
from poc.audio_processor import AudioProcessor
from poc.transcription_engine import TranscriptionEngine

def test_file_handler():
    """Test file validation functionality."""
    print("🧪 Testing FileHandler...")
    
    # Test non-existent file
    is_valid, message = FileHandler.validate_file("nonexistent.mp3")
    print(f"Non-existent file: {is_valid} - {message}")
    
    # Test supported formats detection
    supported = FileHandler.get_supported_formats()
    print(f"Supported formats: {supported}")
    
    # Test format detection
    print(f"Format detection for .mp3: {FileHandler.detect_format('test.mp3')}")
    print(f"Format detection for .mp4: {FileHandler.detect_format('test.mp4')}")
    print(f"Format detection for .txt: {FileHandler.detect_format('test.txt')}")
    
    print("✅ FileHandler tests completed\n")

def test_audio_processor():
    """Test audio processor initialization."""
    print("🧪 Testing AudioProcessor...")
    
    processor = AudioProcessor()
    print(f"Temp audio format: {processor.TEMP_AUDIO_FORMAT}")
    print(f"Sample rate: {processor.SAMPLE_RATE}")
    print(f"Channels: {processor.CHANNELS}")
    
    processor.cleanup_temp_files()
    print("✅ AudioProcessor tests completed\n")

def test_transcription_engine():
    """Test transcription engine initialization."""
    print("🧪 Testing TranscriptionEngine...")
    
    engine = TranscriptionEngine(model_size="tiny")  # Use tiny model for quick test
    
    # Test model info
    model_info = engine.get_model_info()
    print(f"Model info: {model_info}")
    
    print("✅ TranscriptionEngine tests completed\n")

def main():
    """Run all component tests."""
    print("🔬 Running POC Component Tests")
    print("=" * 50)
    
    try:
        test_file_handler()
        test_audio_processor()
        test_transcription_engine()
        
        print("🎉 All component tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)