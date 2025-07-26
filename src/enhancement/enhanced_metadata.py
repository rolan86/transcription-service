"""
Enhanced metadata module for Phase 3D.
Provides detailed transcription metadata, file analysis, and processing statistics.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import hashlib

try:
    import librosa
    import numpy as np
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False

class MetadataEnhancer:
    """Enhances metadata output with detailed information."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.audio_analysis_available = AUDIO_ANALYSIS_AVAILABLE
    
    def generate_enhanced_metadata(self, 
                                  input_file: str,
                                  file_info: Dict[str, Any],
                                  transcription_result: Dict[str, Any],
                                  settings: Dict[str, Any],
                                  processing_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive metadata for transcription.
        
        Args:
            input_file: Path to input file
            file_info: Basic file information
            transcription_result: Transcription results
            settings: Processing settings used
            processing_stats: Performance statistics
            
        Returns:
            Enhanced metadata dictionary
        """
        metadata = {
            'version': '1.0.0-MVP-Phase3',
            'generated_at': datetime.now().isoformat(),
            'generation_timestamp': time.time(),
            'input_file': self._generate_input_file_metadata(input_file, file_info),
            'processing': self._generate_processing_metadata(settings, processing_stats),
            'transcription': self._generate_transcription_metadata(transcription_result),
            'quality_metrics': self._generate_quality_metrics(transcription_result),
            'content_analysis': self._generate_content_analysis(transcription_result),
            'technical_details': self._generate_technical_details(transcription_result, settings)
        }
        
        # Add audio analysis if available and requested
        if self.audio_analysis_available and settings.get('enhanced_metadata_audio_analysis', True):
            try:
                metadata['audio_analysis'] = self._generate_audio_analysis(input_file)
            except Exception as e:
                self.logger.warning(f"Audio analysis failed: {e}")
                metadata['audio_analysis'] = {'available': False, 'error': str(e)}
        
        # Add speaker analysis if speaker detection was used
        if transcription_result.get('speaker_detection', {}).get('enabled'):
            metadata['speaker_analysis'] = self._generate_speaker_analysis(transcription_result)
        
        # Add preprocessing analysis if audio preprocessing was used
        if transcription_result.get('audio_preprocessing', {}).get('enabled'):
            metadata['preprocessing_analysis'] = self._generate_preprocessing_analysis(transcription_result)
        
        return metadata
    
    def _generate_input_file_metadata(self, input_file: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed input file metadata."""
        try:
            file_stat = os.stat(input_file)
            file_path = Path(input_file)
            
            return {
                'path': str(file_path.absolute()),
                'name': file_path.name,
                'stem': file_path.stem,
                'extension': file_path.suffix,
                'directory': str(file_path.parent),
                'size_bytes': file_stat.st_size,
                'size_mb': file_info.get('size_mb', file_stat.st_size / (1024 * 1024)),
                'size_human': self._format_file_size(file_stat.st_size),
                'created_at': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'accessed_at': datetime.fromtimestamp(file_stat.st_atime).isoformat(),
                'format_type': file_info.get('format_type', 'unknown'),
                'mime_type': self._get_mime_type(file_path.suffix),
                'file_hash': self._calculate_file_hash(input_file),
                'permissions': oct(file_stat.st_mode)[-3:]
            }
        except Exception as e:
            self.logger.warning(f"Could not generate input file metadata: {e}")
            return {
                'path': input_file,
                'name': Path(input_file).name,
                'error': str(e)
            }
    
    def _generate_processing_metadata(self, settings: Dict[str, Any], 
                                    processing_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate processing configuration and statistics metadata."""
        processing_metadata = {
            'model': settings.get('transcription', {}).get('default_model', 'unknown'),
            'language': settings.get('transcription', {}).get('default_language', 'auto-detect'),
            'chunk_duration': settings.get('transcription', {}).get('chunk_duration', 30),
            'chunking_used': settings.get('transcription', {}).get('force_chunking', False),
            'timestamps_included': settings.get('output', {}).get('include_timestamps', False),
            'metadata_included': settings.get('output', {}).get('include_metadata', True),
            'features_enabled': {
                'speaker_detection': settings.get('enhancement', {}).get('enable_speaker_detection', False),
                'audio_preprocessing': settings.get('enhancement', {}).get('enable_audio_preprocessing', False),
                'performance_optimizations': settings.get('enhancement', {}).get('enable_performance_optimizations', False),
                'caching': settings.get('enhancement', {}).get('enable_caching', True),
                'memory_optimization': settings.get('enhancement', {}).get('memory_optimization', False)
            },
            'preprocessing_options': {
                'noise_reduction': settings.get('enhancement', {}).get('noise_reduction', False),
                'volume_normalization': settings.get('enhancement', {}).get('volume_normalization', False),
                'high_pass_filter': settings.get('enhancement', {}).get('high_pass_filter', False),
                'low_pass_filter': settings.get('enhancement', {}).get('low_pass_filter', False),
                'enhance_speech': settings.get('enhancement', {}).get('enhance_speech', False),
                'target_sample_rate': settings.get('enhancement', {}).get('target_sample_rate')
            }
        }
        
        # Add performance statistics if available
        if processing_stats:
            processing_metadata['performance'] = {
                'processing_time_seconds': processing_stats.get('processing_time', 0),
                'processing_speed_realtime_factor': processing_stats.get('processing_speed', 0),
                'memory_usage_mb': {
                    'start': processing_stats.get('memory_start', 0),
                    'peak': processing_stats.get('memory_peak', 0),
                    'end': processing_stats.get('memory_end', 0),
                    'used': processing_stats.get('memory_peak', 0) - processing_stats.get('memory_start', 0)
                },
                'cpu_usage_percent': processing_stats.get('cpu_usage', 0),
                'cache_statistics': {
                    'hits': processing_stats.get('cache_hits', 0),
                    'misses': processing_stats.get('cache_misses', 0),
                    'hit_rate': processing_stats.get('cache_hits', 0) / max(1, processing_stats.get('cache_hits', 0) + processing_stats.get('cache_misses', 0))
                }
            }
        
        return processing_metadata
    
    def _generate_transcription_metadata(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate transcription-specific metadata."""
        segments = transcription_result.get('segments', [])
        
        transcription_metadata = {
            'text_length': len(transcription_result.get('text', '')),
            'word_count': transcription_result.get('word_count', 0),
            'character_count': len(transcription_result.get('text', '').replace(' ', '')),
            'segment_count': len(segments),
            'average_confidence': transcription_result.get('confidence', 0),
            'language_detected': transcription_result.get('language', 'unknown'),
            'processing_method': transcription_result.get('processing_method', 'standard'),
            'duration_seconds': self._calculate_total_duration(segments),
            'speaking_rate': self._calculate_speaking_rate(transcription_result.get('text', ''), segments),
            'confidence_distribution': self._calculate_confidence_distribution(segments),
            'segment_statistics': self._calculate_segment_statistics(segments),
            'word_statistics': self._calculate_word_statistics(transcription_result.get('text', ''))
        }
        
        # Add chunk information if available
        if transcription_result.get('chunk_count'):
            transcription_metadata['chunking'] = {
                'total_chunks': transcription_result.get('chunk_count', 0),
                'successful_chunks': transcription_result.get('successful_chunks', 0),
                'failed_chunks': transcription_result.get('failed_chunks', 0),
                'success_rate': transcription_result.get('successful_chunks', 0) / max(1, transcription_result.get('chunk_count', 1))
            }
        
        return transcription_metadata
    
    def _generate_quality_metrics(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate transcription quality metrics."""
        segments = transcription_result.get('segments', [])
        
        # Calculate various quality indicators
        confidence_scores = [seg.get('avg_logprob', 0) for seg in segments if 'avg_logprob' in seg]
        
        quality_metrics = {
            'overall_confidence': transcription_result.get('confidence', 0),
            'confidence_variance': np.var(confidence_scores) if confidence_scores and len(confidence_scores) > 1 else 0,
            'low_confidence_segments': len([s for s in segments if s.get('avg_logprob', 0) < -0.5]),
            'high_confidence_segments': len([s for s in segments if s.get('avg_logprob', 0) > -0.2]),
            'silence_detection': self._analyze_silences(segments),
            'repetition_analysis': self._analyze_repetitions(transcription_result.get('text', '')),
            'length_consistency': self._analyze_segment_length_consistency(segments),
            'quality_score': self._calculate_overall_quality_score(transcription_result),
            'reliability_indicators': self._generate_reliability_indicators(transcription_result)
        }
        
        return quality_metrics
    
    def _generate_content_analysis(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content analysis of the transcription."""
        text = transcription_result.get('text', '')
        
        content_analysis = {
            'sentence_count': len([s for s in text.split('.') if s.strip()]),
            'paragraph_count': len([p for p in text.split('\n') if p.strip()]),
            'average_sentence_length': self._calculate_average_sentence_length(text),
            'vocabulary_diversity': self._calculate_vocabulary_diversity(text),
            'most_common_words': self._get_most_common_words(text, top_n=10),
            'language_patterns': self._analyze_language_patterns(text),
            'punctuation_analysis': self._analyze_punctuation(text),
            'readability_metrics': self._calculate_readability_metrics(text)
        }
        
        return content_analysis
    
    def _generate_technical_details(self, transcription_result: Dict[str, Any], 
                                  settings: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical processing details."""
        return {
            'whisper_model_info': {
                'model_size': settings.get('transcription', {}).get('default_model', 'unknown'),
                'model_parameters': self._get_model_parameters(settings.get('transcription', {}).get('default_model')),
                'computational_requirements': self._get_computational_requirements(settings.get('transcription', {}).get('default_model'))
            },
            'processing_pipeline': self._get_processing_pipeline_info(transcription_result, settings),
            'output_formats': self._get_output_format_info(settings),
            'system_environment': self._get_system_environment_info(),
            'dependencies': self._get_dependency_info()
        }
    
    def _generate_audio_analysis(self, audio_path: str) -> Dict[str, Any]:
        """Generate detailed audio analysis."""
        if not self.audio_analysis_available:
            return {'available': False, 'error': 'librosa not available'}
        
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            
            # Calculate various audio metrics
            audio_analysis = {
                'available': True,
                'sample_rate': int(sr),
                'duration_seconds': len(y) / sr,
                'total_samples': len(y),
                'audio_format': 'mono' if len(y.shape) == 1 else f'{y.shape[1]}-channel',
                'dynamic_range': {
                    'min_amplitude': float(np.min(y)),
                    'max_amplitude': float(np.max(y)),
                    'rms_level': float(np.sqrt(np.mean(y**2))),
                    'peak_level': float(np.max(np.abs(y)))
                },
                'frequency_analysis': {
                    'spectral_centroid_mean': float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))),
                    'spectral_bandwidth_mean': float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))),
                    'spectral_rolloff_mean': float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))),
                    'zero_crossing_rate_mean': float(np.mean(librosa.feature.zero_crossing_rate(y)))
                },
                'energy_analysis': {
                    'mfcc_features': librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13).tolist(),
                    'chroma_features': librosa.feature.chroma(y=y, sr=sr).tolist(),
                    'tonnetz_features': librosa.feature.tonnetz(y=y, sr=sr).tolist()
                },
                'tempo_analysis': {
                    'tempo_bpm': float(librosa.beat.tempo(y=y, sr=sr)[0]),
                    'beat_frames': librosa.beat.beat_track(y=y, sr=sr)[1].tolist()
                }
            }
            
            return audio_analysis
            
        except Exception as e:
            self.logger.warning(f"Audio analysis failed: {e}")
            return {'available': False, 'error': str(e)}
    
    def _generate_speaker_analysis(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate speaker-specific analysis."""
        speaker_data = transcription_result.get('speaker_detection', {})
        
        speaker_analysis = {
            'speaker_count': speaker_data.get('speaker_count', 0),
            'speakers_identified': speaker_data.get('speakers', []),
            'speaker_statistics': speaker_data.get('speaker_stats', {}),
            'speaker_distribution': self._calculate_speaker_distribution(speaker_data),
            'speaker_transitions': self._calculate_speaker_transitions(transcription_result.get('segments', [])),
            'conversation_analysis': self._analyze_conversation_patterns(transcription_result.get('segments', []))
        }
        
        return speaker_analysis
    
    def _generate_preprocessing_analysis(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate audio preprocessing analysis."""
        preprocessing_data = transcription_result.get('audio_preprocessing', {})
        
        preprocessing_analysis = {
            'preprocessing_applied': preprocessing_data.get('preprocessing_applied', []),
            'processing_statistics': preprocessing_data.get('processing_stats', {}),
            'quality_improvements': self._analyze_preprocessing_impact(preprocessing_data),
            'recommendations_followed': len(preprocessing_data.get('preprocessing_applied', [])) > 0
        }
        
        return preprocessing_analysis
    
    # Helper methods for calculations and analysis
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _get_mime_type(self, extension: str) -> str:
        """Get MIME type from file extension."""
        mime_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo'
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return "hash_calculation_failed"
    
    def _calculate_total_duration(self, segments: List[Dict[str, Any]]) -> float:
        """Calculate total duration from segments."""
        if not segments:
            return 0.0
        return max(seg.get('end', 0) for seg in segments)
    
    def _calculate_speaking_rate(self, text: str, segments: List[Dict[str, Any]]) -> float:
        """Calculate words per minute."""
        word_count = len(text.split())
        duration_minutes = self._calculate_total_duration(segments) / 60
        return word_count / duration_minutes if duration_minutes > 0 else 0
    
    def _calculate_confidence_distribution(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate confidence score distribution."""
        confidences = [seg.get('avg_logprob', 0) for seg in segments if 'avg_logprob' in seg]
        if not confidences:
            return {'available': False}
        
        return {
            'available': True,
            'mean': float(np.mean(confidences)),
            'median': float(np.median(confidences)),
            'std': float(np.std(confidences)),
            'min': float(np.min(confidences)),
            'max': float(np.max(confidences)),
            'quartiles': [float(q) for q in np.percentile(confidences, [25, 50, 75])]
        }
    
    def _calculate_segment_statistics(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate segment-level statistics."""
        if not segments:
            return {'available': False}
        
        durations = [seg.get('end', 0) - seg.get('start', 0) for seg in segments]
        word_counts = [len(seg.get('text', '').split()) for seg in segments]
        
        return {
            'available': True,
            'duration_stats': {
                'mean': float(np.mean(durations)),
                'median': float(np.median(durations)),
                'std': float(np.std(durations)),
                'min': float(np.min(durations)),
                'max': float(np.max(durations))
            },
            'word_count_stats': {
                'mean': float(np.mean(word_counts)),
                'median': float(np.median(word_counts)),
                'std': float(np.std(word_counts)),
                'min': int(np.min(word_counts)),
                'max': int(np.max(word_counts))
            }
        }
    
    def _calculate_word_statistics(self, text: str) -> Dict[str, Any]:
        """Calculate word-level statistics."""
        words = text.split()
        if not words:
            return {'available': False}
        
        word_lengths = [len(word.strip('.,!?";:')) for word in words]
        
        return {
            'available': True,
            'total_words': len(words),
            'unique_words': len(set(words)),
            'average_word_length': float(np.mean(word_lengths)),
            'longest_word': max(words, key=len) if words else '',
            'shortest_word': min(words, key=len) if words else ''
        }
    
    def _analyze_silences(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze silence patterns between segments."""
        if len(segments) < 2:
            return {'available': False}
        
        silences = []
        for i in range(len(segments) - 1):
            silence_duration = segments[i + 1].get('start', 0) - segments[i].get('end', 0)
            if silence_duration > 0:
                silences.append(silence_duration)
        
        if not silences:
            return {'available': False}
        
        return {
            'available': True,
            'silence_count': len(silences),
            'total_silence_duration': float(np.sum(silences)),
            'average_silence_duration': float(np.mean(silences)),
            'longest_silence': float(np.max(silences)),
            'shortest_silence': float(np.min(silences))
        }
    
    def _analyze_repetitions(self, text: str) -> Dict[str, Any]:
        """Analyze word and phrase repetitions."""
        words = text.lower().split()
        if not words:
            return {'available': False}
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        repeated_words = {word: count for word, count in word_counts.items() if count > 1}
        
        return {
            'available': True,
            'repeated_word_count': len(repeated_words),
            'most_repeated_words': sorted(repeated_words.items(), key=lambda x: x[1], reverse=True)[:5],
            'repetition_ratio': len(repeated_words) / len(word_counts) if word_counts else 0
        }
    
    def _analyze_segment_length_consistency(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze consistency of segment lengths."""
        if len(segments) < 2:
            return {'available': False}
        
        durations = [seg.get('end', 0) - seg.get('start', 0) for seg in segments]
        coefficient_of_variation = np.std(durations) / np.mean(durations) if np.mean(durations) > 0 else 0
        
        return {
            'available': True,
            'coefficient_of_variation': float(coefficient_of_variation),
            'consistency_rating': 'high' if coefficient_of_variation < 0.5 else 'medium' if coefficient_of_variation < 1.0 else 'low'
        }
    
    def _calculate_overall_quality_score(self, transcription_result: Dict[str, Any]) -> float:
        """Calculate overall quality score (0-100)."""
        score = 50.0  # Base score
        
        # Confidence contribution (40 points max)
        confidence = transcription_result.get('confidence', 0)
        score += confidence * 40
        
        # Segment consistency (20 points max)
        segments = transcription_result.get('segments', [])
        if segments:
            confidences = [seg.get('avg_logprob', 0) for seg in segments if 'avg_logprob' in seg]
            if confidences:
                consistency = 1 - (np.std(confidences) / abs(np.mean(confidences))) if np.mean(confidences) != 0 else 0
                score += max(0, consistency * 20)
        
        # Processing success (20 points max)
        if transcription_result.get('success', False):
            score += 20
        
        # Additional bonuses for features
        if transcription_result.get('speaker_detection', {}).get('enabled'):
            score += 5
        if transcription_result.get('audio_preprocessing', {}).get('enabled'):
            score += 5
        
        return min(100.0, max(0.0, score))
    
    def _generate_reliability_indicators(self, transcription_result: Dict[str, Any]) -> List[str]:
        """Generate reliability indicators for the transcription."""
        indicators = []
        
        confidence = transcription_result.get('confidence', 0)
        if confidence > 0.8:
            indicators.append("High confidence score")
        elif confidence < 0.5:
            indicators.append("Low confidence score - review recommended")
        
        segments = transcription_result.get('segments', [])
        if segments:
            low_conf_segments = len([s for s in segments if s.get('avg_logprob', 0) < -0.5])
            if low_conf_segments > len(segments) * 0.2:
                indicators.append("Multiple low-confidence segments detected")
        
        if transcription_result.get('speaker_detection', {}).get('enabled'):
            indicators.append("Speaker detection enabled - enhanced accuracy")
        
        if transcription_result.get('audio_preprocessing', {}).get('enabled'):
            indicators.append("Audio preprocessing applied - improved quality")
        
        if transcription_result.get('from_cache'):
            indicators.append("Result from cache - identical to previous processing")
        
        return indicators
    
    def _calculate_average_sentence_length(self, text: str) -> float:
        """Calculate average sentence length in words."""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return 0
        
        word_counts = [len(sentence.split()) for sentence in sentences]
        return float(np.mean(word_counts))
    
    def _calculate_vocabulary_diversity(self, text: str) -> float:
        """Calculate vocabulary diversity (unique words / total words)."""
        words = text.lower().split()
        if not words:
            return 0
        
        return len(set(words)) / len(words)
    
    def _get_most_common_words(self, text: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get most common words in the text."""
        words = [word.lower().strip('.,!?";:') for word in text.split()]
        word_counts = {}
        
        for word in words:
            if word and len(word) > 2:  # Exclude very short words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'word': word, 'count': count} for word, count in sorted_words[:top_n]]
    
    def _analyze_language_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze language patterns in the text."""
        return {
            'question_count': text.count('?'),
            'exclamation_count': text.count('!'),
            'uppercase_ratio': len([c for c in text if c.isupper()]) / len(text) if text else 0,
            'digit_ratio': len([c for c in text if c.isdigit()]) / len(text) if text else 0
        }
    
    def _analyze_punctuation(self, text: str) -> Dict[str, Any]:
        """Analyze punctuation usage."""
        punctuation_counts = {
            'periods': text.count('.'),
            'commas': text.count(','),
            'questions': text.count('?'),
            'exclamations': text.count('!'),
            'semicolons': text.count(';'),
            'colons': text.count(':')
        }
        
        total_punct = sum(punctuation_counts.values())
        
        return {
            'counts': punctuation_counts,
            'total_punctuation': total_punct,
            'punctuation_density': total_punct / len(text) if text else 0
        }
    
    def _calculate_readability_metrics(self, text: str) -> Dict[str, Any]:
        """Calculate basic readability metrics."""
        sentences = len([s for s in text.split('.') if s.strip()])
        words = len(text.split())
        characters = len(text.replace(' ', ''))
        
        if sentences == 0 or words == 0:
            return {'available': False}
        
        avg_sentence_length = words / sentences
        avg_word_length = characters / words
        
        return {
            'available': True,
            'average_sentence_length': avg_sentence_length,
            'average_word_length': avg_word_length,
            'complexity_score': (avg_sentence_length * 0.5) + (avg_word_length * 2.0)
        }
    
    def _get_model_parameters(self, model_size: str) -> Dict[str, Any]:
        """Get model parameter information."""
        model_params = {
            'tiny': {'parameters': '39M', 'memory_required': '~1GB'},
            'base': {'parameters': '74M', 'memory_required': '~1GB'},
            'small': {'parameters': '244M', 'memory_required': '~2GB'},
            'medium': {'parameters': '769M', 'memory_required': '~5GB'},
            'large': {'parameters': '1550M', 'memory_required': '~10GB'}
        }
        return model_params.get(model_size, {'parameters': 'unknown', 'memory_required': 'unknown'})
    
    def _get_computational_requirements(self, model_size: str) -> Dict[str, Any]:
        """Get computational requirements for model."""
        requirements = {
            'tiny': {'cpu_suitable': True, 'gpu_recommended': False, 'processing_speed': 'fast'},
            'base': {'cpu_suitable': True, 'gpu_recommended': False, 'processing_speed': 'fast'},
            'small': {'cpu_suitable': True, 'gpu_recommended': True, 'processing_speed': 'medium'},
            'medium': {'cpu_suitable': False, 'gpu_recommended': True, 'processing_speed': 'medium'},
            'large': {'cpu_suitable': False, 'gpu_recommended': True, 'processing_speed': 'slow'}
        }
        return requirements.get(model_size, {'cpu_suitable': True, 'gpu_recommended': False, 'processing_speed': 'unknown'})
    
    def _get_processing_pipeline_info(self, transcription_result: Dict[str, Any], 
                                    settings: Dict[str, Any]) -> List[str]:
        """Get information about the processing pipeline used."""
        pipeline = ['Audio extraction/conversion']
        
        if transcription_result.get('audio_preprocessing', {}).get('enabled'):
            pipeline.append('Audio preprocessing')
        
        if transcription_result.get('chunk_count'):
            pipeline.append('Chunked processing')
        else:
            pipeline.append('Standard processing')
        
        pipeline.append('Whisper transcription')
        
        if transcription_result.get('speaker_detection', {}).get('enabled'):
            pipeline.append('Speaker diarization')
        
        pipeline.append('Output formatting')
        
        return pipeline
    
    def _get_output_format_info(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Get output format information."""
        return {
            'format': settings.get('output', {}).get('default_format', 'txt'),
            'metadata_included': settings.get('output', {}).get('include_metadata', True),
            'timestamps_included': settings.get('output', {}).get('include_timestamps', False)
        }
    
    def _get_system_environment_info(self) -> Dict[str, Any]:
        """Get system environment information."""
        import platform
        import sys
        
        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor() or 'unknown'
        }
    
    def _get_dependency_info(self) -> Dict[str, Any]:
        """Get dependency version information."""
        dependencies = {}
        
        try:
            import whisper
            dependencies['openai-whisper'] = whisper.__version__
        except ImportError:
            dependencies['openai-whisper'] = 'not_available'
        
        try:
            import librosa
            dependencies['librosa'] = librosa.__version__
        except ImportError:
            dependencies['librosa'] = 'not_available'
        
        try:
            import torch
            dependencies['torch'] = torch.__version__
        except ImportError:
            dependencies['torch'] = 'not_available'
        
        return dependencies
    
    def _calculate_speaker_distribution(self, speaker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate speaker time distribution."""
        speaker_stats = speaker_data.get('speaker_stats', {})
        if not speaker_stats:
            return {'available': False}
        
        total_time = sum(stats.get('total_duration', 0) for stats in speaker_stats.values())
        
        distribution = {}
        for speaker, stats in speaker_stats.items():
            duration = stats.get('total_duration', 0)
            distribution[speaker] = {
                'duration_seconds': duration,
                'percentage': (duration / total_time * 100) if total_time > 0 else 0,
                'segment_count': stats.get('segment_count', 0)
            }
        
        return {
            'available': True,
            'total_speaking_time': total_time,
            'speaker_distribution': distribution
        }
    
    def _calculate_speaker_transitions(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate speaker transition patterns."""
        if len(segments) < 2:
            return {'available': False}
        
        transitions = 0
        prev_speaker = None
        
        for segment in segments:
            current_speaker = segment.get('speaker')
            if current_speaker and prev_speaker and current_speaker != prev_speaker:
                transitions += 1
            prev_speaker = current_speaker
        
        return {
            'available': True,
            'total_transitions': transitions,
            'average_segments_per_speaker': len(segments) / (transitions + 1) if transitions >= 0 else len(segments)
        }
    
    def _analyze_conversation_patterns(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation patterns between speakers."""
        if not segments:
            return {'available': False}
        
        speakers_with_segments = [seg for seg in segments if seg.get('speaker')]
        if len(speakers_with_segments) < 2:
            return {'available': False}
        
        # Calculate turn-taking metrics
        speaker_turns = []
        current_speaker = None
        turn_length = 0
        
        for segment in speakers_with_segments:
            speaker = segment.get('speaker')
            if speaker != current_speaker:
                if current_speaker and turn_length > 0:
                    speaker_turns.append(turn_length)
                current_speaker = speaker
                turn_length = 1
            else:
                turn_length += 1
        
        if turn_length > 0:
            speaker_turns.append(turn_length)
        
        return {
            'available': True,
            'average_turn_length': float(np.mean(speaker_turns)) if speaker_turns else 0,
            'turn_length_variance': float(np.var(speaker_turns)) if speaker_turns else 0,
            'conversation_style': 'interactive' if np.mean(speaker_turns) < 3 else 'monologue-heavy' if np.mean(speaker_turns) > 10 else 'balanced'
        }
    
    def _analyze_preprocessing_impact(self, preprocessing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the impact of audio preprocessing."""
        processing_stats = preprocessing_data.get('processing_stats', {})
        
        if not processing_stats:
            return {'available': False}
        
        original_rms = processing_stats.get('original_rms', 0)
        final_rms = processing_stats.get('final_rms', 0)
        
        return {
            'available': True,
            'volume_change': {
                'original_rms': original_rms,
                'final_rms': final_rms,
                'change_db': 20 * np.log10(final_rms / original_rms) if original_rms > 0 else 0
            },
            'sample_rate_change': {
                'original': processing_stats.get('original_sample_rate'),
                'final': processing_stats.get('final_sample_rate')
            },
            'duration_change': {
                'original': processing_stats.get('original_duration'),
                'final': processing_stats.get('final_duration')
            }
        }