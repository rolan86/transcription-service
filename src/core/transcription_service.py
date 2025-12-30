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
from enhancement.speaker_detection import SpeakerDetector, is_speaker_detection_available
from enhancement.audio_preprocessing import AudioPreprocessor, AudioAnalyzer
from enhancement.performance_optimizations import (
    CacheManager, MemoryOptimizer, ParallelProcessor, PerformanceMonitor
)
from enhancement.enhanced_metadata import MetadataEnhancer


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
        self.speaker_detector = None  # Lazy initialization
        self.audio_preprocessor = None  # Lazy initialization
        self.audio_analyzer = None  # Lazy initialization
        
        # Performance optimization components
        self.cache_manager = None  # Lazy initialization
        self.memory_optimizer = None  # Lazy initialization
        self.performance_monitor = None  # Lazy initialization
        
        # Enhanced metadata component
        self.metadata_enhancer = None  # Lazy initialization
        
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
        
        # Initialize performance monitoring if enabled
        performance_monitoring = None
        if self.settings.get('enhancement', 'show_performance_metrics', False):
            if self.performance_monitor is None:
                self.performance_monitor = PerformanceMonitor(self.logger)
            performance_monitoring = self.performance_monitor.start_monitoring()
        
        # Initialize cache manager if caching is enabled
        if self.settings.get('enhancement', 'enable_caching', True):
            if self.cache_manager is None:
                cache_dir = self.settings.get('enhancement', 'cache_directory')
                self.cache_manager = CacheManager(cache_dir=cache_dir)
        
        try:
            self.progress_logger.info(f"🎙️ Starting transcription of {input_file}")
            
            # Check cache first if enabled
            cached_result = None
            if self.cache_manager:
                model = self.settings.get('transcription', 'default_model', 'base')
                language = self.settings.get('transcription', 'default_language')
                settings_hash = self._generate_settings_hash()
                cached_result = self.cache_manager.get_transcription_cache(
                    input_file, model, language, settings_hash
                )
                
                if cached_result:
                    self.progress_logger.info("🎯 Using cached transcription result")
                    # Update timing and add cache info
                    cached_result['processing_time'] = time.time() - start_time
                    cached_result['from_cache'] = True
                    if performance_monitoring:
                        cached_result['performance_stats'] = self.performance_monitor.end_monitoring(
                            performance_monitoring, cached_result.get('duration', 0)
                        )
                    return cached_result
            
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
            
            # Step 2.5: Speaker Detection (if enabled)
            if self.settings.get('enhancement', 'enable_speaker_detection', False):
                result = self._process_speaker_detection(input_file, result, file_info['format_type'])
            
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
                'language': result.get('language', 'unknown'),
                'from_cache': False
            }
            
            # Add performance stats if monitoring was enabled
            if performance_monitoring:
                audio_duration = result.get('duration', 0)
                performance_stats = self.performance_monitor.end_monitoring(performance_monitoring, audio_duration)
                final_result['performance_stats'] = performance_stats
                
                if self.settings.get('enhancement', 'show_performance_metrics', False):
                    performance_report = self.performance_monitor.format_performance_report(performance_stats)
                    self.progress_logger.info(f"\n{performance_report}")
            
            # Cache result if caching is enabled
            if self.cache_manager:
                model = self.settings.get('transcription', 'default_model', 'base')
                language = self.settings.get('transcription', 'default_language')
                settings_hash = self._generate_settings_hash()
                self.cache_manager.set_transcription_cache(
                    input_file, model, language, settings_hash, final_result
                )
            
            # Perform memory optimization if enabled
            if self.settings.get('enhancement', 'memory_optimization', False):
                if self.memory_optimizer is None:
                    self.memory_optimizer = MemoryOptimizer(self.logger)
                memory_result = self.memory_optimizer.optimize_memory_usage(aggressive=True)
                if memory_result.get('success') and memory_result.get('memory_freed_mb', 0) > 0:
                    self.progress_logger.info(f"🧹 Freed {memory_result['memory_freed_mb']:.1f} MB of memory")
            
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
            
            # Check if parallel processing should be used
            parallel_workers = self.settings.get('enhancement', 'parallel_workers')
            use_parallel = (
                self.settings.get('enhancement', 'enable_performance_optimizations', False) and
                len(files) > 1 and 
                parallel_workers is not None and parallel_workers > 1
            )
            
            processed_files = 0
            failed_files = []
            
            if use_parallel:
                self.progress_logger.info(f"🚀 Using parallel processing with {parallel_workers} workers")
                
                # Prepare file processing tasks
                file_tasks = []
                for file_path in files:
                    relative_path = Path(file_path).relative_to(input_dir)
                    output_file = Path(output_dir) / relative_path.with_suffix(f'.{output_format}')
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    file_tasks.append((str(file_path), str(output_file), output_format))
                
                # Create parallel processor
                parallel_processor = ParallelProcessor(
                    max_workers=parallel_workers,
                    use_processes=False,  # Use threads to share state
                    logger=self.logger
                )
                
                # Define processing function
                def process_single_file(task):
                    file_path, output_file, fmt = task
                    return self.transcribe_file(file_path, output_file, fmt)
                
                # Process files in parallel
                results = parallel_processor.process_batch(file_tasks, process_single_file)
                
                # Collect results
                for i, (result, (file_path, _, _)) in enumerate(zip(results, file_tasks)):
                    if result.get('success'):
                        processed_files += 1
                        self.progress_logger.file_processed(
                            Path(file_path).name,
                            result.get('processing_time', 0),
                            True
                        )
                    else:
                        failed_files.append({
                            'file': file_path,
                            'error': result.get('error', 'Unknown error')
                        })
                        self.progress_logger.file_processed(
                            Path(file_path).name,
                            result.get('processing_time', 0),
                            False
                        )
            else:
                # Sequential processing
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

        # Apply audio preprocessing if enabled
        final_audio_path = audio_path
        preprocessing_result = None

        if self.settings.get('enhancement', 'analyze_audio_quality', False):
            preprocessing_result = self._analyze_audio_quality(audio_path)

        if self.settings.get('enhancement', 'enable_audio_preprocessing', False):
            preprocessing_result = self._process_audio_preprocessing(audio_path)
            if preprocessing_result and preprocessing_result.get('success'):
                final_audio_path = preprocessing_result['processed_file']
                self.progress_logger.info(f"🔧 Audio preprocessing completed: {', '.join(preprocessing_result['preprocessing_applied'])}")

        # Transcribe
        if not self.transcription_engine:
            model = self.settings.get('transcription', 'default_model', 'base')
            whisper_config = self.settings.whisper_config
            self.transcription_engine = TranscriptionEngine(model_size=model, whisper_config=whisper_config)

        language = self.settings.get('transcription', 'default_language')

        # Get initial prompt for custom vocabulary
        initial_prompt = self.settings.get('transcription', 'initial_prompt')

        result = self.transcription_engine.transcribe_audio(
            final_audio_path, language, initial_prompt=initial_prompt
        )

        # Add preprocessing information to result
        if preprocessing_result:
            result['audio_preprocessing'] = preprocessing_result

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
    
    def _process_speaker_detection(self, input_file: str, transcription_result: Dict[str, Any], 
                                  file_type: str) -> Dict[str, Any]:
        """
        Process speaker detection and merge with transcription results.
        
        Args:
            input_file: Path to input file
            transcription_result: Results from transcription
            file_type: Type of file (audio or video)
            
        Returns:
            Enhanced transcription result with speaker information
        """
        try:
            if not is_speaker_detection_available():
                self.progress_logger.info("⚠️  Speaker detection not available (pyannote.audio not installed)")
                transcription_result['speaker_detection_error'] = "pyannote.audio not installed"
                return transcription_result
            
            # Initialize speaker detector if needed
            if self.speaker_detector is None:
                enable_hf_token = self.settings.get('enhancement', 'use_huggingface_token', False)
                self.speaker_detector = SpeakerDetector(enable_huggingface_token=enable_hf_token)
            
            self.progress_logger.info("🎭 Performing speaker detection...")
            
            # Get audio file path
            audio_path = input_file
            if file_type == 'video':
                # Use the processed audio path from audio processor
                success, message, audio_path = self.audio_processor.process_file(input_file, file_type)
                if not success:
                    transcription_result['speaker_detection_error'] = f"Audio extraction failed: {message}"
                    return transcription_result
            
            # Perform speaker detection
            num_speakers = self.settings.get('enhancement', 'expected_speakers')
            speaker_result = self.speaker_detector.detect_speakers(audio_path, num_speakers)
            
            if not speaker_result['success']:
                self.progress_logger.info(f"⚠️  Speaker detection failed: {speaker_result['error']}")
                transcription_result['speaker_detection_error'] = speaker_result['error']
                return transcription_result
            
            # Merge speaker info with transcription segments
            transcription_segments = transcription_result.get('segments', [])
            if transcription_segments:
                merged_segments = self.speaker_detector.merge_with_transcription(
                    transcription_segments, 
                    speaker_result['speaker_segments']
                )
                transcription_result['segments'] = merged_segments
            
            # Add speaker detection results
            transcription_result.update({
                'speaker_detection': {
                    'enabled': True,
                    'speaker_count': speaker_result['speaker_count'],
                    'speakers': speaker_result['speakers'],
                    'speaker_stats': speaker_result['speaker_stats'],
                    'speaker_segments': speaker_result['speaker_segments']
                }
            })
            
            # Update formatted text with speaker labels if requested
            if self.settings.get('enhancement', 'include_speaker_labels', True):
                speaker_formatted_text = self.speaker_detector.format_speaker_output(
                    merged_segments if transcription_segments else [],
                    include_confidence=self.settings.get('enhancement', 'include_speaker_confidence', False)
                )
                transcription_result['speaker_formatted_text'] = speaker_formatted_text
            
            self.progress_logger.info(f"✅ Speaker detection completed: {speaker_result['speaker_count']} speakers found")
            return transcription_result
            
        except Exception as e:
            self.progress_logger.info(f"⚠️  Speaker detection error: {str(e)}")
            transcription_result['speaker_detection_error'] = str(e)
            return transcription_result
    
    def _process_audio_preprocessing(self, audio_path: str) -> Dict[str, Any]:
        """
        Apply audio preprocessing to improve transcription quality.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with preprocessing results
        """
        try:
            # Initialize audio preprocessor if needed
            if self.audio_preprocessor is None:
                self.audio_preprocessor = AudioPreprocessor(self.logger)
            
            if not self.audio_preprocessor.available:
                self.progress_logger.info("⚠️  Audio preprocessing not available (dependencies not installed)")
                return {
                    'enabled': False,
                    'processed_file': audio_path,
                    'error': 'Audio preprocessing dependencies not available'
                }
            
            self.progress_logger.info("🔧 Applying audio preprocessing...")
            
            # Get preprocessing settings
            temp_dir = self.settings.get('processing', 'temp_dir')
            noise_reduction = self.settings.get('enhancement', 'noise_reduction', False)
            volume_normalization = self.settings.get('enhancement', 'volume_normalization', False)
            high_pass_filter = self.settings.get('enhancement', 'high_pass_filter', False)
            low_pass_filter = self.settings.get('enhancement', 'low_pass_filter', False)
            enhance_speech = self.settings.get('enhancement', 'enhance_speech', False)
            target_sample_rate = self.settings.get('enhancement', 'target_sample_rate')
            
            # Apply preprocessing
            result = self.audio_preprocessor.preprocess_audio(
                audio_path=audio_path,
                temp_dir=temp_dir,
                noise_reduction=noise_reduction,
                volume_normalization=volume_normalization,
                high_pass_filter=high_pass_filter,
                low_pass_filter=low_pass_filter,
                target_sample_rate=target_sample_rate,
                enhance_speech=enhance_speech
            )
            
            if result['enabled'] and result.get('success'):
                applied = result['preprocessing_applied']
                if applied:
                    self.progress_logger.info(f"✅ Applied: {', '.join(applied)}")
                else:
                    self.progress_logger.info("ℹ️  No preprocessing needed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Audio preprocessing error: {str(e)}")
            return {
                'enabled': True,
                'processed_file': audio_path,
                'error': str(e),
                'success': False
            }
    
    def _analyze_audio_quality(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio quality and provide recommendations.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with analysis results and recommendations
        """
        try:
            # Initialize audio analyzer if needed
            if self.audio_analyzer is None:
                self.audio_analyzer = AudioAnalyzer(self.logger)
            
            if not self.audio_analyzer.available:
                self.progress_logger.info("⚠️  Audio analysis not available (dependencies not installed)")
                return {
                    'available': False,
                    'error': 'Audio analysis dependencies not available'
                }
            
            self.progress_logger.info("📊 Analyzing audio quality...")
            
            # Analyze audio
            result = self.audio_analyzer.analyze_audio_quality(audio_path)
            
            if result.get('success'):
                quality_score = result.get('quality_score', 0)
                recommendations = result.get('recommendations', {})
                
                self.progress_logger.info(f"📊 Audio quality score: {quality_score:.1f}/100")
                
                # Show recommendations if any
                rec_reasons = recommendations.get('reasons', [])
                if rec_reasons:
                    self.progress_logger.info("💡 Recommendations:")
                    for reason in rec_reasons:
                        self.progress_logger.info(f"   • {reason}")
                    
                    # Show suggested preprocessing options
                    suggested = []
                    if recommendations.get('noise_reduction'):
                        suggested.append('--noise-reduction')
                    if recommendations.get('volume_normalization'):
                        suggested.append('--volume-normalize')
                    if recommendations.get('high_pass_filter'):
                        suggested.append('--high-pass-filter')
                    if recommendations.get('enhance_speech'):
                        suggested.append('--enhance-speech')
                    if recommendations.get('resample'):
                        suggested.append('--target-sample-rate 16000')
                    
                    if suggested:
                        self.progress_logger.info(f"   Try: --preprocess {' '.join(suggested)}")
                else:
                    self.progress_logger.info("✅ Audio quality looks good!")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Audio quality analysis error: {str(e)}")
            return {
                'available': True,
                'error': str(e),
                'success': False
            }
    
    def _generate_settings_hash(self) -> str:
        """Generate hash from relevant settings for caching."""
        import hashlib
        
        # Include settings that affect transcription output
        relevant_settings = {
            'model': self.settings.get('transcription', 'default_model', 'base'),
            'language': self.settings.get('transcription', 'default_language'),
            'chunk_duration': self.settings.get('transcription', 'chunk_duration', 30),
            'force_chunking': self.settings.get('transcription', 'force_chunking', False),
            'speakers': self.settings.get('enhancement', 'enable_speaker_detection', False),
            'expected_speakers': self.settings.get('enhancement', 'expected_speakers'),
            'preprocess': self.settings.get('enhancement', 'enable_audio_preprocessing', False),
            'noise_reduction': self.settings.get('enhancement', 'noise_reduction', False),
            'volume_norm': self.settings.get('enhancement', 'volume_normalization', False),
            'high_pass': self.settings.get('enhancement', 'high_pass_filter', False),
            'low_pass': self.settings.get('enhancement', 'low_pass_filter', False),
            'enhance_speech': self.settings.get('enhancement', 'enhance_speech', False),
            'target_sr': self.settings.get('enhancement', 'target_sample_rate')
        }
        
        settings_str = str(sorted(relevant_settings.items()))
        return hashlib.md5(settings_str.encode()).hexdigest()[:8]
    
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