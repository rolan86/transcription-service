#!/usr/bin/env python3
"""
Enhanced POC Transcription Script with Large File Support
Supports MP3, WAV, and MP4 files with automatic chunking for large files.

Usage:
    python transcribe_large_poc.py <file_path> [--model base] [--timestamps] [--language en] [--force-chunking]
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from poc.file_handler import FileHandler
from poc.audio_processor import AudioProcessor
from poc.transcription_engine import TranscriptionEngine
from poc.chunked_processor import ChunkedProcessor


def print_separator():
    """Print a visual separator."""
    print("=" * 60)


def print_file_info(file_info: dict):
    """Print formatted file information."""
    print(f"📁 File: {file_info['name']}")
    print(f"📏 Size: {file_info['size_mb']} MB")
    print(f"🎵 Type: {file_info['format_type']}")
    print(f"📍 Path: {file_info['path']}")


def print_transcription_results(result: dict, include_timestamps: bool = False):
    """Print formatted transcription results."""
    if not result['success']:
        print(f"❌ Transcription failed: {result.get('error', 'Unknown error')}")
        return
    
    print(f"✅ Transcription completed successfully!")
    print(f"🌍 Language: {result['language']}")
    print(f"⏱️  Processing time: {result['processing_time']}s")
    print(f"📊 Confidence: {result['confidence']:.1%}")
    print(f"📝 Word count: {result['word_count']}")
    print(f"🔢 Segments: {result['segment_count']}")
    
    # Show chunking info if available
    if 'chunk_count' in result:
        print(f"📦 Chunks processed: {result['chunk_count']}")
        if result.get('failed_chunks', 0) > 0:
            print(f"⚠️  Failed chunks: {result['failed_chunks']}")
    
    print_separator()
    print("📄 TRANSCRIPT:")
    print_separator()
    
    # Format and print transcript
    engine = TranscriptionEngine()
    formatted_text = engine.format_transcript(result, include_timestamps)
    print(formatted_text)


def main():
    """Main enhanced POC transcription function."""
    parser = argparse.ArgumentParser(
        description="Enhanced POC Transcription Service - Convert audio/video to text with large file support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcribe_large_poc.py audio.mp3
  python transcribe_large_poc.py long_video.mp4 --timestamps
  python transcribe_large_poc.py recording.wav --model small --language en
  python transcribe_large_poc.py huge_file.mp4 --force-chunking
        """
    )
    
    parser.add_argument(
        'file_path',
        help='Path to audio (MP3, WAV) or video (MP4) file'
    )
    
    parser.add_argument(
        '--model',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        default='base',
        help='Whisper model size (default: base)'
    )
    
    parser.add_argument(
        '--timestamps',
        action='store_true',
        help='Include timestamps in output'
    )
    
    parser.add_argument(
        '--language',
        help='Language code (e.g., en, es, fr) or auto-detect if not specified'
    )
    
    parser.add_argument(
        '--force-chunking',
        action='store_true',
        help='Force chunked processing even for small files'
    )
    
    parser.add_argument(
        '--chunk-duration',
        type=int,
        default=30,
        help='Chunk duration in seconds for large files (default: 30)'
    )
    
    args = parser.parse_args()
    
    print_separator()
    print("🎙️  ENHANCED POC TRANSCRIPTION SERVICE")
    print_separator()
    
    # Step 1: Validate file
    print("1️⃣  Validating input file...")
    is_valid, message = FileHandler.validate_file(args.file_path)
    
    if not is_valid:
        print(f"❌ {message}")
        return 1
    
    print(f"✅ {message}")
    
    # Get file information
    file_info = FileHandler.get_file_info(args.file_path)
    print_file_info(file_info)
    print()
    
    # Step 2: Determine processing strategy
    chunked_processor = ChunkedProcessor(chunk_duration=args.chunk_duration)
    use_chunking = args.force_chunking or chunked_processor.should_use_chunking(
        args.file_path, file_info['format_type']
    )
    
    if use_chunking:
        print("2️⃣  Large file detected - using chunked processing...")
        try:
            duration = chunked_processor.get_file_duration(args.file_path)
            print(f"📏 File duration: {duration/60:.1f} minutes ({duration:.1f}s)")
            print(f"📦 Will create ~{int(duration/args.chunk_duration)} chunks")
            print()
            
            # Process with chunking
            result = chunked_processor.process_large_file(
                args.file_path,
                file_info['format_type'],
                model_size=args.model,
                language=args.language
            )
            
            # Print results
            print()
            print_transcription_results(result, include_timestamps=args.timestamps)
            
            return 0 if result['success'] else 1
            
        except Exception as e:
            print(f"❌ Chunked processing failed: {str(e)}")
            return 1
        finally:
            chunked_processor.cleanup()
    
    else:
        print("2️⃣  Standard processing (small file)...")
        
        # Use original POC approach for small files
        processor = AudioProcessor()
        
        try:
            success, message, audio_path = processor.process_file(
                args.file_path, 
                file_info['format_type']
            )
            
            if not success:
                print(f"❌ {message}")
                return 1
            
            print(f"✅ {message}")
            
            # Get audio information
            audio_info = processor.get_audio_info(audio_path)
            if 'error' not in audio_info:
                print(f"⏱️  Duration: {audio_info['duration_formatted']} ({audio_info['duration_seconds']:.1f}s)")
                print(f"🔊 Channels: {audio_info['channels']}")
                print(f"📊 Sample Rate: {audio_info['frame_rate']} Hz")
            print()
            
            # Step 3: Transcribe
            print("3️⃣  Transcribing audio...")
            engine = TranscriptionEngine(model_size=args.model)
            
            # Show model info
            model_info = engine.get_model_info()
            print(f"🤖 Model: {model_info['model_size']} on {model_info['device']}")
            if model_info['gpu_available']:
                print(f"🚀 GPU: {model_info['gpu_device']}")
            
            # Perform transcription
            result = engine.transcribe_audio(audio_path, language=args.language)
            
            # Print results
            print()
            print_transcription_results(result, include_timestamps=args.timestamps)
            
            return 0 if result['success'] else 1
            
        except KeyboardInterrupt:
            print("\n❌ Transcription interrupted by user")
            return 1
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return 1
        finally:
            # Cleanup temporary files
            processor.cleanup_temp_files()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)