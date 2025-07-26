"""
Output writers for different transcript formats.
Supports TXT, JSON, and future format extensions.
"""

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from config.settings import Settings
from enhancement.enhanced_metadata import MetadataEnhancer


class BaseWriter(ABC):
    """Abstract base class for output writers."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.metadata_enhancer = None  # Lazy initialization
    
    @abstractmethod
    def write(self, transcription_result: Dict[str, Any], output_path: str, 
              file_info: Dict[str, Any]):
        """Write transcription result to file."""
        pass
    
    def _generate_metadata(self, transcription_result: Dict[str, Any], 
                          file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata for the transcription."""
        # Check if enhanced metadata is enabled
        if self.settings.get('enhancement', 'enhanced_metadata', False):
            return self._generate_enhanced_metadata(transcription_result, file_info)
        
        # Standard metadata
        return {
            'timestamp': datetime.now().isoformat(),
            'input_file': {
                'name': file_info['name'],
                'path': file_info['path'],
                'size_mb': file_info['size_mb'],
                'format_type': file_info['format_type']
            },
            'transcription': {
                'model': self.settings.get('transcription', 'default_model', 'base'),
                'language': transcription_result.get('language', 'unknown'),
                'processing_time': transcription_result.get('processing_time', 0),
                'confidence': transcription_result.get('confidence', 0),
                'word_count': transcription_result.get('word_count', 0),
                'segment_count': transcription_result.get('segment_count', 0)
            },
            'chunks': {
                'chunk_count': transcription_result.get('chunk_count', 0),
                'successful_chunks': transcription_result.get('successful_chunks', 0),
                'failed_chunks': transcription_result.get('failed_chunks', 0)
            } if 'chunk_count' in transcription_result else None,
            'version': '1.0.0-MVP'
        }
    
    def _generate_enhanced_metadata(self, transcription_result: Dict[str, Any], 
                                   file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced metadata with detailed analysis."""
        if self.metadata_enhancer is None:
            self.metadata_enhancer = MetadataEnhancer()
        
        # Get enhanced metadata settings
        settings_dict = {
            'transcription': self.settings.config.get('transcription', {}),
            'output': self.settings.config.get('output', {}),
            'enhancement': self.settings.config.get('enhancement', {}),
            'enhanced_metadata_audio_analysis': self.settings.get('enhancement', 'enhanced_metadata_audio_analysis', True),
            'enhanced_metadata_content_analysis': self.settings.get('enhancement', 'enhanced_metadata_content_analysis', True)
        }
        
        # Get performance stats if available
        performance_stats = transcription_result.get('performance_stats')
        if hasattr(performance_stats, '__dict__'):
            performance_stats = performance_stats.__dict__
        
        # Generate enhanced metadata
        return self.metadata_enhancer.generate_enhanced_metadata(
            input_file=file_info['path'],
            file_info=file_info,
            transcription_result=transcription_result,
            settings=settings_dict,
            processing_stats=performance_stats
        )


class TextWriter(BaseWriter):
    """Writer for plain text format."""
    
    def write(self, transcription_result: Dict[str, Any], output_path: str, 
              file_info: Dict[str, Any]):
        """Write transcription as plain text."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write header if metadata is enabled
                if self.settings.get('output', 'include_metadata', True):
                    metadata = self._generate_metadata(transcription_result, file_info)
                    
                    f.write("# Transcription\n")
                    f.write(f"# File: {metadata['input_file']['name']}\n")
                    f.write(f"# Generated: {metadata['timestamp']}\n")
                    f.write(f"# Model: {metadata['transcription']['model']}\n")
                    f.write(f"# Language: {metadata['transcription']['language']}\n")
                    f.write(f"# Processing time: {metadata['transcription']['processing_time']:.2f}s\n")
                    f.write(f"# Confidence: {metadata['transcription']['confidence']:.1%}\n")
                    
                    if metadata['chunks']:
                        f.write(f"# Chunks: {metadata['chunks']['chunk_count']} total, "
                               f"{metadata['chunks']['successful_chunks']} successful\n")
                    
                    f.write("\n" + "="*50 + "\n\n")
                
                # Write transcript text
                # Check if speaker-formatted text is available
                if 'speaker_formatted_text' in transcription_result and transcription_result['speaker_formatted_text']:
                    text = transcription_result['speaker_formatted_text']
                    f.write(text)
                else:
                    text = transcription_result.get('text', '').strip()
                    if text:
                        # Format with timestamps if requested
                        if self.settings.get('output', 'include_timestamps', False):
                            text = self._format_text_with_timestamps(transcription_result)
                        
                        f.write(text)
                    else:
                        f.write("No speech detected in audio.")
                
                # Add speaker summary if speaker detection was used
                if transcription_result.get('speaker_detection', {}).get('enabled'):
                    speaker_stats = transcription_result['speaker_detection'].get('speaker_stats', {})
                    if speaker_stats:
                        f.write("\n\n" + "="*50 + "\n")
                        f.write("SPEAKER SUMMARY\n")
                        f.write("="*50 + "\n")
                        sorted_speakers = sorted(
                            speaker_stats.items(),
                            key=lambda x: x[1]['total_duration'],
                            reverse=True
                        )
                        for i, (speaker, stats) in enumerate(sorted_speakers, 1):
                            duration = stats['total_duration']
                            segments = stats['segment_count']
                            f.write(f"{i}. {speaker}: {duration:.1f}s ({segments} segments)\n")
                
                f.write("\n")
                
        except Exception as e:
            raise RuntimeError(f"Failed to write text file {output_path}: {str(e)}")
    
    def _format_text_with_timestamps(self, transcription_result: Dict[str, Any]) -> str:
        """Format text with timestamps."""
        segments = transcription_result.get('segments', [])
        if not segments:
            return transcription_result.get('text', '')
        
        formatted_lines = []
        for segment in segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '').strip()
            
            if text:
                timestamp = f"[{self._format_time(start_time)} -> {self._format_time(end_time)}]"
                formatted_lines.append(f"{timestamp} {text}")
        
        return '\n'.join(formatted_lines)
    
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"


class JSONWriter(BaseWriter):
    """Writer for JSON format."""
    
    def write(self, transcription_result: Dict[str, Any], output_path: str, 
              file_info: Dict[str, Any]):
        """Write transcription as structured JSON."""
        try:
            # Prepare JSON structure
            output_data = {
                'metadata': self._generate_metadata(transcription_result, file_info),
                'transcription': {
                    'text': transcription_result.get('text', ''),
                    'language': transcription_result.get('language', 'unknown'),
                    'confidence': transcription_result.get('confidence', 0),
                    'processing_time': transcription_result.get('processing_time', 0),
                    'word_count': transcription_result.get('word_count', 0),
                    'segment_count': transcription_result.get('segment_count', 0)
                },
                'segments': self._format_segments(transcription_result.get('segments', [])),
                'statistics': {
                    'total_duration': self._calculate_total_duration(transcription_result.get('segments', [])),
                    'average_confidence': transcription_result.get('confidence', 0),
                    'processing_speed': self._calculate_processing_speed(transcription_result)
                }
            }
            
            # Add chunk information if available
            if 'chunk_count' in transcription_result:
                output_data['chunks'] = {
                    'total': transcription_result.get('chunk_count', 0),
                    'successful': transcription_result.get('successful_chunks', 0),
                    'failed': transcription_result.get('failed_chunks', 0)
                }
            
            # Add speaker detection information if available
            if 'speaker_detection' in transcription_result:
                speaker_data = transcription_result['speaker_detection']
                output_data['speaker_detection'] = {
                    'enabled': speaker_data.get('enabled', False),
                    'speaker_count': speaker_data.get('speaker_count', 0),
                    'speakers': speaker_data.get('speakers', []),
                    'speaker_stats': speaker_data.get('speaker_stats', {}),
                    'speaker_segments': speaker_data.get('speaker_segments', [])
                }
                
                # Add speaker-formatted text if available
                if 'speaker_formatted_text' in transcription_result:
                    output_data['speaker_formatted_text'] = transcription_result['speaker_formatted_text']
            
            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise RuntimeError(f"Failed to write JSON file {output_path}: {str(e)}")
    
    def _format_segments(self, segments: list) -> list:
        """Format segments for JSON output."""
        formatted_segments = []
        
        for segment in segments:
            formatted_segment = {
                'start': segment.get('start', 0),
                'end': segment.get('end', 0),
                'text': segment.get('text', '').strip(),
                'confidence': segment.get('avg_logprob', 0)
            }
            
            # Add speaker information if available
            if 'speaker' in segment:
                formatted_segment['speaker'] = segment['speaker']
                if 'speaker_confidence' in segment:
                    formatted_segment['speaker_confidence'] = segment['speaker_confidence']
            
            # Add word-level information if available
            if 'words' in segment:
                formatted_segment['words'] = [
                    {
                        'word': word.get('word', ''),
                        'start': word.get('start', 0),
                        'end': word.get('end', 0),
                        'confidence': word.get('probability', 0)
                    }
                    for word in segment['words']
                ]
            
            formatted_segments.append(formatted_segment)
        
        return formatted_segments
    
    def _calculate_total_duration(self, segments: list) -> float:
        """Calculate total duration from segments."""
        if not segments:
            return 0.0
        
        return max(segment.get('end', 0) for segment in segments)
    
    def _calculate_processing_speed(self, transcription_result: Dict[str, Any]) -> float:
        """Calculate processing speed (realtime factor)."""
        processing_time = transcription_result.get('processing_time', 0)
        segments = transcription_result.get('segments', [])
        
        if not segments or processing_time == 0:
            return 0.0
        
        audio_duration = self._calculate_total_duration(segments)
        return audio_duration / processing_time if processing_time > 0 else 0.0


class SRTWriter(BaseWriter):
    """Writer for SRT subtitle format."""
    
    def write(self, transcription_result: Dict[str, Any], output_path: str, 
              file_info: Dict[str, Any]):
        """Write transcription as SRT subtitle file."""
        try:
            segments = transcription_result.get('segments', [])
            if not segments:
                # If no segments, create a single subtitle from the text
                text = transcription_result.get('text', '').strip()
                if text:
                    segments = [{'start': 0, 'end': 30, 'text': text}]
                else:
                    segments = [{'start': 0, 'end': 1, 'text': 'No speech detected in audio.'}]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    start_time = segment.get('start', 0)
                    end_time = segment.get('end', start_time + 1)
                    text = segment.get('text', '').strip()
                    
                    if text:
                        # SRT format:
                        # 1
                        # 00:00:00,000 --> 00:00:04,000
                        # Subtitle text
                        # (blank line)
                        f.write(f"{i}\n")
                        f.write(f"{self._format_srt_time(start_time)} --> {self._format_srt_time(end_time)}\n")
                        f.write(f"{text}\n\n")
                        
        except Exception as e:
            raise RuntimeError(f"Failed to write SRT file {output_path}: {str(e)}")
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time in SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


class VTTWriter(BaseWriter):
    """Writer for WebVTT subtitle format."""
    
    def write(self, transcription_result: Dict[str, Any], output_path: str, 
              file_info: Dict[str, Any]):
        """Write transcription as WebVTT subtitle file."""
        try:
            segments = transcription_result.get('segments', [])
            if not segments:
                # If no segments, create a single subtitle from the text
                text = transcription_result.get('text', '').strip()
                if text:
                    segments = [{'start': 0, 'end': 30, 'text': text}]
                else:
                    segments = [{'start': 0, 'end': 1, 'text': 'No speech detected in audio.'}]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                # WebVTT header
                f.write("WEBVTT\n\n")
                
                # Add metadata as note if enabled
                if self.settings.get('output', 'include_metadata', True):
                    metadata = self._generate_metadata(transcription_result, file_info)
                    f.write("NOTE\n")
                    f.write(f"Generated by Professional Transcription Service\n")
                    f.write(f"File: {metadata['input_file']['name']}\n")
                    f.write(f"Model: {metadata['transcription']['model']}\n")
                    f.write(f"Language: {metadata['transcription']['language']}\n")
                    f.write(f"Confidence: {metadata['transcription']['confidence']:.1%}\n\n")
                
                for segment in segments:
                    start_time = segment.get('start', 0)
                    end_time = segment.get('end', start_time + 1)
                    text = segment.get('text', '').strip()
                    
                    if text:
                        # WebVTT format:
                        # 00:00:00.000 --> 00:00:04.000
                        # Subtitle text
                        # (blank line)
                        f.write(f"{self._format_vtt_time(start_time)} --> {self._format_vtt_time(end_time)}\n")
                        f.write(f"{text}\n\n")
                        
        except Exception as e:
            raise RuntimeError(f"Failed to write VTT file {output_path}: {str(e)}")
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format time in WebVTT format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


class OutputWriterFactory:
    """Factory for creating output writers."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._writers = {
            'txt': TextWriter,
            'json': JSONWriter,
            'srt': SRTWriter,
            'vtt': VTTWriter
        }
    
    def create_writer(self, format_type: str) -> BaseWriter:
        """Create writer for specified format."""
        format_type = format_type.lower()
        
        if format_type not in self._writers:
            raise ValueError(f"Unsupported output format: {format_type}. "
                           f"Supported formats: {list(self._writers.keys())}")
        
        writer_class = self._writers[format_type]
        return writer_class(self.settings)
    
    def get_supported_formats(self) -> list:
        """Get list of supported output formats."""
        return list(self._writers.keys())