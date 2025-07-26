"""
Core transcription service that orchestrates the entire transcription process.
Integrates file handling, processing, and output generation.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Import POC components (we'll enhance these)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'poc'))

from poc.file_handler import FileHandler
from poc.audio_processor import AudioProcessor
from poc.transcription_engine import TranscriptionEngine
from poc.chunked_processor import ChunkedProcessor

from config.settings import Settings
from output.writers import OutputWriterFactory
from utils.logger import ProgressLogger


class TranscriptionService:
    """Main service class that orchestrates transcription operations."""
    
    def __init__(self, settings: Settings, logger: logging.Logger):
        """
        Initialize transcription service.
        
        Args:
            settings: Configuration settings
            logger: Logger instance
        """
        self.settings = settings
        self.logger = logger
        self.progress_logger = ProgressLogger(logger, settings.get('processing', 'quiet_mode', False))
        
        # Initialize components
        self.file_handler = FileHandler()
        self.audio_processor = AudioProcessor()
        self.transcription_engine = None  # Lazy initialization
        self.chunked_processor = None  # Lazy initialization
        
        # Initialize output writer factory
        self.output_writer_factory = OutputWriterFactory(settings)
    
    def transcribe_file(self, input_file: str, output_file: Optional[str] = None, 
                       output_format: str = 'txt') -> Dict[str, Any]:
        """
        Transcribe a single file.
        
        Args:
            input_file: Path to input file
            output_file: Optional output file path
            output_format: Output format ('txt' or 'json')
            
        Returns:
            Dictionary with transcription results
        """
        start_time = time.time()
        
        try:
            self.progress_logger.info(f"🎙️ Starting transcription of {input_file}")
            
            # Step 1: Validate input file
            # Skip size check if force chunking is enabled or if we'll use chunking anyway
            force_chunking = self.settings.get('transcription', 'force_chunking', False)
            max_memory_mb = self.settings.get('transcription', 'max_memory_mb', 1000)
            skip_size_check = force_chunking
            
            is_valid, message = self.file_handler.validate_file(
                input_file, 
                skip_size_check=skip_size_check, 
                max_size_mb=max_memory_mb
            )
            if not is_valid:
                return {
                    'success': False,
                    'error': message,
                    'processing_time': 0
                }
            
            # Get file information
            file_info = self.file_handler.get_file_info(input_file)
            self.progress_logger.info(f"📁 File: {file_info['name']} ({file_info['size_mb']} MB)")
            
            # Step 2: Determine processing strategy
            if self._should_use_chunking(input_file, file_info['format_type']):
                self.progress_logger.info("📦 Using chunked processing for large file")
                result = self._process_with_chunking(input_file, file_info['format_type'])
            else:
                self.progress_logger.info("🔄 Using standard processing")
                result = self._process_standard(input_file, file_info['format_type'])
            
            if not result['success']:
                return result
            
            # Step 3: Generate output file path if not provided
            if not output_file:
                output_file = self._generate_output_filename(input_file, output_format)
            
            # Step 4: Write output
            writer = self.output_writer_factory.create_writer(output_format)
            writer.write(result, output_file, file_info)
            
            # Step 5: Prepare final result
            processing_time = time.time() - start_time
            final_result = {
                'success': True,
                'output_file': output_file,
                'processing_time': processing_time,
                'text': result['text'],
                'confidence': result.get('confidence', 0),
                'word_count': result.get('word_count', 0),
                'language': result.get('language', 'unknown')
            }
            
            self.progress_logger.info(f"✅ Transcription completed in {processing_time:.2f}s")
            return final_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Transcription failed: {str(e)}"
            self.progress_logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'processing_time': processing_time
            }
        finally:
            # Cleanup
            if hasattr(self, 'audio_processor'):
                self.audio_processor.cleanup_temp_files()
            if hasattr(self, 'chunked_processor') and self.chunked_processor:
                self.chunked_processor.cleanup()
    
    def batch_transcribe(self, input_dir: str, output_dir: Optional[str] = None,
                        output_format: str = 'txt', recursive: bool = False) -> Dict[str, Any]:
        """
        Batch transcribe multiple files in a directory.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            output_format: Output format
            recursive: Process subdirectories recursively
            
        Returns:
            Dictionary with batch processing results
        """
        start_time = time.time()
        
        try:
            # Find all supported files
            files = self._find_supported_files(input_dir, recursive)
            
            if not files:
                return {
                    'success': False,
                    'error': f'No supported audio/video files found in {input_dir}',
                    'total_files': 0,
                    'processed_files': 0,
                    'total_time': 0
                }
            
            self.progress_logger.info(f"📁 Found {len(files)} files to process")
            
            # Set up output directory
            if not output_dir:
                output_dir = input_dir
            else:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Process files
            processed_files = 0
            failed_files = []
            
            for i, file_path in enumerate(files, 1):
                self.progress_logger.progress(f"Processing {Path(file_path).name}", i, len(files))
                
                # Generate output path
                relative_path = Path(file_path).relative_to(input_dir)
                output_file = Path(output_dir) / relative_path.with_suffix(f'.{output_format}')
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Process file
                result = self.transcribe_file(str(file_path), str(output_file), output_format)
                
                if result['success']:
                    processed_files += 1
                    self.progress_logger.file_processed(
                        Path(file_path).name, 
                        result['processing_time'], 
                        True
                    )
                else:
                    failed_files.append({
                        'file': str(file_path),
                        'error': result['error']
                    })
                    self.progress_logger.file_processed(
                        Path(file_path).name, 
                        result.get('processing_time', 0), 
                        False
                    )
            
            # Generate summary
            total_time = time.time() - start_time
            self.progress_logger.batch_summary(processed_files, len(files), total_time)
            
            return {
                'success': True,
                'total_files': len(files),
                'processed_files': processed_files,
                'failed_files': failed_files,
                'total_time': total_time
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"Batch processing failed: {str(e)}"
            self.progress_logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'total_files': 0,
                'processed_files': 0,
                'total_time': total_time
            }
    
    def _should_use_chunking(self, file_path: str, file_type: str) -> bool:
        """Determine if chunking should be used."""
        # Check force chunking setting
        if self.settings.get('transcription', 'force_chunking', False):
            return True
        
        # Use chunked processor's logic
        if not self.chunked_processor:
            chunk_duration = self.settings.get('transcription', 'chunk_duration', 30)
            self.chunked_processor = ChunkedProcessor(chunk_duration=chunk_duration)
        
        return self.chunked_processor.should_use_chunking(file_path, file_type)
    
    def _process_standard(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Process file using standard (non-chunked) approach."""
        # Process audio
        success, message, audio_path = self.audio_processor.process_file(file_path, file_type)
        if not success:
            return {'success': False, 'error': message}
        
        # Transcribe
        if not self.transcription_engine:
            model = self.settings.get('transcription', 'default_model', 'base')
            whisper_config = self.settings.whisper_config
            self.transcription_engine = TranscriptionEngine(model_size=model, whisper_config=whisper_config)
        
        language = self.settings.get('transcription', 'default_language')
        result = self.transcription_engine.transcribe_audio(audio_path, language)
        
        return result
    
    def _process_with_chunking(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Process file using chunked approach."""
        if not self.chunked_processor:
            chunk_duration = self.settings.get('transcription', 'chunk_duration', 30)
            self.chunked_processor = ChunkedProcessor(chunk_duration=chunk_duration)
        
        model = self.settings.get('transcription', 'default_model', 'base')
        language = self.settings.get('transcription', 'default_language')
        
        return self.chunked_processor.process_large_file(file_path, file_type, model, language)
    
    def _generate_output_filename(self, input_file: str, output_format: str) -> str:
        """Generate output filename based on input file."""
        input_path = Path(input_file)
        return str(input_path.with_suffix(f'.{output_format}'))
    
    def _find_supported_files(self, directory: str, recursive: bool = False) -> List[str]:
        """Find all supported audio/video files in directory."""
        supported_extensions = self.file_handler.get_supported_formats()
        files = []
        
        search_pattern = "**/*" if recursive else "*"
        
        for file_path in Path(directory).glob(search_pattern):
            if (file_path.is_file() and 
                file_path.suffix.lower() in supported_extensions):
                files.append(str(file_path))
        
        return sorted(files)