"""
Chunked processor for handling large audio/video files.
Implements memory-efficient processing for files of any size.
"""

import os
import tempfile
import math
from pathlib import Path
from typing import List, Dict, Iterator, Tuple, Optional
from dataclasses import dataclass
import ffmpeg
from tqdm import tqdm

from .transcription_engine import TranscriptionEngine


@dataclass
class ChunkInfo:
    """Information about a processing chunk."""
    index: int
    start_time: float
    end_time: float
    duration: float
    file_path: str
    size_bytes: int = 0


@dataclass 
class ProcessingProgress:
    """Progress information for chunked processing."""
    current_chunk: int
    total_chunks: int
    current_chunk_info: ChunkInfo
    elapsed_time: float
    estimated_remaining: float
    percentage: float


class ChunkedProcessor:
    """Handles large file processing through chunking strategy."""
    
    def __init__(self, chunk_duration: int = 30, max_memory_mb: int = 500):
        """
        Initialize chunked processor.
        
        Args:
            chunk_duration: Duration of each chunk in seconds
            max_memory_mb: Maximum memory usage target in MB
        """
        self.chunk_duration = chunk_duration
        self.max_memory_mb = max_memory_mb
        self.temp_files: List[str] = []
        self.transcription_engine = None
        
    def __del__(self):
        """Cleanup temporary files."""
        self.cleanup()
        
    def cleanup(self):
        """Remove all temporary chunk files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Could not remove temp file {temp_file}: {e}")
        self.temp_files.clear()
    
    def should_use_chunking(self, file_path: str, file_type: str) -> bool:
        """
        Determine if file should be processed in chunks.
        
        Args:
            file_path: Path to the file
            file_type: Type of file ('audio' or 'video')
            
        Returns:
            True if chunking should be used
        """
        # Get file duration using ffmpeg
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            
            # Use chunking for files longer than 5 minutes
            return duration > 300  # 5 minutes
            
        except Exception:
            # If we can't determine duration, assume small file
            return False
    
    def get_file_duration(self, file_path: str) -> float:
        """
        Get file duration in seconds.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Duration in seconds
        """
        try:
            probe = ffmpeg.probe(file_path)
            return float(probe['format']['duration'])
        except Exception as e:
            raise RuntimeError(f"Could not determine file duration: {str(e)}")
    
    def create_audio_chunks(self, file_path: str, file_type: str) -> List[ChunkInfo]:
        """
        Create audio chunks from source file.
        
        Args:
            file_path: Path to the source file
            file_type: Type of file ('audio' or 'video')
            
        Returns:
            List of chunk information
        """
        duration = self.get_file_duration(file_path)
        chunk_count = math.ceil(duration / self.chunk_duration)
        chunks = []
        
        print(f"📦 Creating {chunk_count} chunks ({self.chunk_duration}s each) from {duration:.1f}s file")
        
        for i in range(chunk_count):
            start_time = i * self.chunk_duration
            end_time = min((i + 1) * self.chunk_duration, duration)
            chunk_duration = end_time - start_time
            
            # Create temporary file for chunk
            temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
            os.close(temp_fd)
            self.temp_files.append(temp_path)
            
            try:
                # Extract chunk using ffmpeg
                if file_type == 'video':
                    # Extract audio from video with time range
                    (
                        ffmpeg
                        .input(file_path, ss=start_time, t=chunk_duration)
                        .output(
                            temp_path,
                            acodec='pcm_s16le',
                            ac=1,  # Mono
                            ar=16000  # 16kHz
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                else:
                    # Extract chunk from audio file
                    (
                        ffmpeg
                        .input(file_path, ss=start_time, t=chunk_duration)
                        .output(
                            temp_path,
                            acodec='pcm_s16le',
                            ac=1,  # Mono
                            ar=16000  # 16kHz
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                
                # Get chunk file size
                size_bytes = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                
                chunk_info = ChunkInfo(
                    index=i,
                    start_time=start_time,
                    end_time=end_time,
                    duration=chunk_duration,
                    file_path=temp_path,
                    size_bytes=size_bytes
                )
                chunks.append(chunk_info)
                
            except ffmpeg.Error as e:
                error_msg = f"FFmpeg error creating chunk {i}: {e.stderr.decode() if e.stderr else str(e)}"
                raise RuntimeError(error_msg)
        
        return chunks
    
    def transcribe_chunks(self, chunks: List[ChunkInfo], model_size: str = "base", 
                         language: Optional[str] = None) -> List[Dict]:
        """
        Transcribe all chunks with progress tracking.
        
        Args:
            chunks: List of chunk information
            model_size: Whisper model size
            language: Language code or None for auto-detection
            
        Returns:
            List of transcription results with timing information
        """
        if not self.transcription_engine:
            self.transcription_engine = TranscriptionEngine(model_size)
        
        results = []
        
        # Use tqdm for progress bar
        with tqdm(total=len(chunks), desc="🎙️ Transcribing chunks", unit="chunk") as pbar:
            for chunk in chunks:
                # Update progress bar description
                start_min = int(chunk.start_time // 60)
                start_sec = int(chunk.start_time % 60)
                end_min = int(chunk.end_time // 60)
                end_sec = int(chunk.end_time % 60)
                
                pbar.set_description(f"🎙️ Chunk {chunk.index+1}/{len(chunks)} ({start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d})")
                
                # Transcribe chunk
                result = self.transcription_engine.transcribe_audio(chunk.file_path, language)
                
                if result['success']:
                    # Adjust timestamps to global time
                    if result['segments']:
                        for segment in result['segments']:
                            segment['start'] += chunk.start_time
                            segment['end'] += chunk.start_time
                    
                    # Add chunk metadata
                    result['chunk_info'] = {
                        'index': chunk.index,
                        'start_time': chunk.start_time,
                        'end_time': chunk.end_time,
                        'file_size_mb': chunk.size_bytes / (1024 * 1024)
                    }
                
                results.append(result)
                pbar.update(1)
                
                # Clean up chunk file immediately to save space
                try:
                    if os.path.exists(chunk.file_path):
                        os.remove(chunk.file_path)
                        self.temp_files.remove(chunk.file_path)
                except Exception as e:
                    print(f"Warning: Could not remove chunk file: {e}")
        
        return results
    
    def merge_results(self, chunk_results: List[Dict]) -> Dict:
        """
        Merge chunk transcription results into a single result.
        
        Args:
            chunk_results: List of chunk transcription results
            
        Returns:
            Merged transcription result
        """
        if not chunk_results:
            return {'success': False, 'error': 'No chunks to merge', 'text': ''}
        
        # Filter successful results
        successful_results = [r for r in chunk_results if r['success']]
        
        if not successful_results:
            return {'success': False, 'error': 'No successful chunk transcriptions', 'text': ''}
        
        # Merge text
        merged_text = ' '.join(r['text'].strip() for r in successful_results if r['text'])
        
        # Merge segments
        all_segments = []
        for result in successful_results:
            if result.get('segments'):
                all_segments.extend(result['segments'])
        
        # Calculate overall statistics
        total_processing_time = sum(r.get('processing_time', 0) for r in successful_results)
        avg_confidence = sum(r.get('confidence', 0) for r in successful_results) / len(successful_results)
        total_words = sum(r.get('word_count', 0) for r in successful_results)
        
        # Detect most common language
        languages = [r.get('language', 'unknown') for r in successful_results]
        most_common_language = max(set(languages), key=languages.count) if languages else 'unknown'
        
        return {
            'success': True,
            'text': merged_text,
            'segments': all_segments,
            'language': most_common_language,
            'confidence': round(avg_confidence, 3),
            'processing_time': round(total_processing_time, 2),
            'word_count': total_words,
            'segment_count': len(all_segments),
            'chunk_count': len(chunk_results),
            'successful_chunks': len(successful_results),
            'failed_chunks': len(chunk_results) - len(successful_results)
        }
    
    def process_large_file(self, file_path: str, file_type: str, model_size: str = "base",
                          language: Optional[str] = None) -> Dict:
        """
        Process large file using chunking strategy.
        
        Args:
            file_path: Path to the source file
            file_type: Type of file ('audio' or 'video')
            model_size: Whisper model size
            language: Language code or None for auto-detection
            
        Returns:
            Transcription result
        """
        try:
            print(f"🔄 Processing large file with chunking strategy")
            
            # Create chunks
            chunks = self.create_audio_chunks(file_path, file_type)
            print(f"✅ Created {len(chunks)} chunks")
            
            # Calculate total audio size
            total_size_mb = sum(chunk.size_bytes for chunk in chunks) / (1024 * 1024)
            print(f"📊 Total audio size: {total_size_mb:.1f} MB")
            
            # Transcribe chunks
            chunk_results = self.transcribe_chunks(chunks, model_size, language)
            
            # Merge results
            final_result = self.merge_results(chunk_results)
            
            print(f"✅ Chunked processing completed!")
            print(f"📊 Processed {final_result['chunk_count']} chunks")
            print(f"✅ Successful: {final_result['successful_chunks']}")
            if final_result['failed_chunks'] > 0:
                print(f"❌ Failed: {final_result['failed_chunks']}")
            
            return final_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Chunked processing failed: {str(e)}",
                'text': '',
                'segments': [],
                'chunk_count': 0
            }
        finally:
            # Cleanup any remaining temp files
            self.cleanup()