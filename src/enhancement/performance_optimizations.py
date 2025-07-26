"""
Performance optimization module for Phase 3C.
Provides multi-threading, caching, memory optimization, and processing speed improvements.
"""

import os
import gc
import threading
import multiprocessing
import time
import hashlib
import pickle
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from dataclasses import dataclass

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

@dataclass
class ProcessingStats:
    """Statistics for processing performance monitoring."""
    start_time: float
    end_time: float
    memory_start: float
    memory_peak: float
    memory_end: float
    cpu_usage: float
    processing_speed: float  # realtime factor
    cache_hits: int = 0
    cache_misses: int = 0

class CacheManager:
    """Manages caching for transcription results and processed audio."""
    
    def __init__(self, cache_dir: Optional[str] = None, max_cache_size_mb: int = 1000):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files (default: system temp)
            max_cache_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "transcription_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # Convert to bytes
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Create subdirectories
        (self.cache_dir / "transcriptions").mkdir(exist_ok=True)
        (self.cache_dir / "audio_processing").mkdir(exist_ok=True)
        (self.cache_dir / "speaker_detection").mkdir(exist_ok=True)
    
    def _generate_cache_key(self, content: str, prefix: str = "") -> str:
        """Generate cache key from content."""
        hash_obj = hashlib.sha256(content.encode())
        return f"{prefix}_{hash_obj.hexdigest()[:16]}"
    
    def _get_cache_path(self, cache_type: str, cache_key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / cache_type / f"{cache_key}.pkl"
    
    def _cleanup_cache(self):
        """Remove old cache files if cache size exceeds limit."""
        try:
            total_size = 0
            cache_files = []
            
            # Collect all cache files with their sizes and modification times
            for cache_subdir in ["transcriptions", "audio_processing", "speaker_detection"]:
                subdir = self.cache_dir / cache_subdir
                if subdir.exists():
                    for cache_file in subdir.glob("*.pkl"):
                        stat = cache_file.stat()
                        total_size += stat.st_size
                        cache_files.append((cache_file, stat.st_size, stat.st_mtime))
            
            # If cache is too large, remove oldest files
            if total_size > self.max_cache_size:
                # Sort by modification time (oldest first)
                cache_files.sort(key=lambda x: x[2])
                
                bytes_to_remove = total_size - self.max_cache_size
                bytes_removed = 0
                
                for cache_file, file_size, _ in cache_files:
                    if bytes_removed >= bytes_to_remove:
                        break
                    
                    try:
                        cache_file.unlink()
                        bytes_removed += file_size
                    except Exception:
                        pass  # Ignore errors when removing cache files
                        
        except Exception:
            pass  # Ignore errors in cache cleanup
    
    def get_transcription_cache(self, file_path: str, model: str, language: Optional[str] = None,
                               settings_hash: str = "") -> Optional[Dict[str, Any]]:
        """Get cached transcription result."""
        try:
            # Create cache key from file path, size, modification time, model, and settings
            file_stat = os.stat(file_path)
            cache_content = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}_{model}_{language}_{settings_hash}"
            cache_key = self._generate_cache_key(cache_content, "transcription")
            cache_path = self._get_cache_path("transcriptions", cache_key)
            
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    result = pickle.load(f)
                self.cache_hits += 1
                return result
            else:
                self.cache_misses += 1
                return None
                
        except Exception:
            self.cache_misses += 1
            return None
    
    def set_transcription_cache(self, file_path: str, model: str, language: Optional[str] = None,
                               settings_hash: str = "", result: Dict[str, Any] = None):
        """Cache transcription result."""
        try:
            # Create cache key
            file_stat = os.stat(file_path)
            cache_content = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}_{model}_{language}_{settings_hash}"
            cache_key = self._generate_cache_key(cache_content, "transcription")
            cache_path = self._get_cache_path("transcriptions", cache_key)
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
            
            # Cleanup if needed
            self._cleanup_cache()
            
        except Exception:
            pass  # Ignore cache write errors
    
    def get_audio_processing_cache(self, file_path: str, processing_settings: str) -> Optional[str]:
        """Get cached processed audio file path."""
        try:
            file_stat = os.stat(file_path)
            cache_content = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}_{processing_settings}"
            cache_key = self._generate_cache_key(cache_content, "audio")
            cache_path = self._get_cache_path("audio_processing", cache_key)
            
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    cached_audio_path = pickle.load(f)
                
                # Check if cached audio file still exists
                if os.path.exists(cached_audio_path):
                    self.cache_hits += 1
                    return cached_audio_path
            
            self.cache_misses += 1
            return None
            
        except Exception:
            self.cache_misses += 1
            return None
    
    def set_audio_processing_cache(self, file_path: str, processing_settings: str, processed_path: str):
        """Cache processed audio file path."""
        try:
            file_stat = os.stat(file_path)
            cache_content = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}_{processing_settings}"
            cache_key = self._generate_cache_key(cache_content, "audio")
            cache_path = self._get_cache_path("audio_processing", cache_key)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(processed_path, f)
                
        except Exception:
            pass
    
    def clear_cache(self, cache_type: Optional[str] = None):
        """Clear cache files."""
        try:
            if cache_type:
                cache_subdir = self.cache_dir / cache_type
                if cache_subdir.exists():
                    for cache_file in cache_subdir.glob("*.pkl"):
                        cache_file.unlink()
            else:
                # Clear all cache
                for cache_subdir in ["transcriptions", "audio_processing", "speaker_detection"]:
                    subdir = self.cache_dir / cache_subdir
                    if subdir.exists():
                        for cache_file in subdir.glob("*.pkl"):
                            cache_file.unlink()
        except Exception:
            pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            total_files = 0
            total_size = 0
            
            for cache_subdir in ["transcriptions", "audio_processing", "speaker_detection"]:
                subdir = self.cache_dir / cache_subdir
                if subdir.exists():
                    for cache_file in subdir.glob("*.pkl"):
                        total_files += 1
                        total_size += cache_file.stat().st_size
            
            hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            
            return {
                'total_files': total_files,
                'total_size_mb': total_size / (1024 * 1024),
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'hit_rate': hit_rate,
                'cache_dir': str(self.cache_dir)
            }
        except Exception:
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'hit_rate': 0,
                'cache_dir': str(self.cache_dir)
            }


class MemoryOptimizer:
    """Optimizes memory usage during transcription processing."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.available = PSUTIL_AVAILABLE
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        if not self.available:
            return {'available': False}
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return {
                'available': True,
                'process_rss_mb': memory_info.rss / (1024 * 1024),
                'process_vms_mb': memory_info.vms / (1024 * 1024),
                'system_total_mb': system_memory.total / (1024 * 1024),
                'system_used_mb': system_memory.used / (1024 * 1024),
                'system_available_mb': system_memory.available / (1024 * 1024),
                'system_percent': system_memory.percent
            }
        except Exception as e:
            self.logger.warning(f"Could not get memory usage: {e}")
            return {'available': False}
    
    def optimize_memory_usage(self, aggressive: bool = False) -> Dict[str, Any]:
        """Optimize memory usage."""
        try:
            memory_before = self.get_memory_usage()
            
            # Force garbage collection
            collected = gc.collect()
            
            if aggressive:
                # More aggressive memory cleanup
                import sys
                import ctypes
                
                # Clear caches
                if hasattr(sys, 'intern'):
                    # Clear string intern cache
                    sys.intern.__dict__.clear()
                
                # Force memory compaction (Python 3.8+)
                if hasattr(gc, 'compact'):
                    gc.compact()
            
            memory_after = self.get_memory_usage()
            
            memory_freed = 0
            if memory_before.get('available') and memory_after.get('available'):
                memory_freed = memory_before['process_rss_mb'] - memory_after['process_rss_mb']
            
            return {
                'memory_freed_mb': memory_freed,
                'objects_collected': collected,
                'memory_before': memory_before,
                'memory_after': memory_after,
                'success': True
            }
            
        except Exception as e:
            self.logger.warning(f"Memory optimization failed: {e}")
            return {
                'memory_freed_mb': 0,
                'objects_collected': 0,
                'success': False,
                'error': str(e)
            }
    
    def check_memory_pressure(self, threshold_percent: float = 80.0) -> Dict[str, Any]:
        """Check if system is under memory pressure."""
        memory_info = self.get_memory_usage()
        
        if not memory_info.get('available'):
            return {'available': False}
        
        under_pressure = memory_info['system_percent'] > threshold_percent
        
        return {
            'available': True,
            'under_pressure': under_pressure,
            'system_memory_percent': memory_info['system_percent'],
            'threshold_percent': threshold_percent,
            'recommendation': 'Consider using chunked processing or reducing chunk size' if under_pressure else 'Memory usage is normal'
        }


class ParallelProcessor:
    """Handles parallel processing for batch operations."""
    
    def __init__(self, max_workers: Optional[int] = None, use_processes: bool = False,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize parallel processor.
        
        Args:
            max_workers: Maximum number of worker threads/processes
            use_processes: Use processes instead of threads
            logger: Logger instance
        """
        self.max_workers = max_workers or min(4, multiprocessing.cpu_count())
        self.use_processes = use_processes
        self.logger = logger or logging.getLogger(__name__)
    
    def process_batch(self, items: List[Any], process_func: Callable,
                     show_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Process items in parallel.
        
        Args:
            items: List of items to process
            process_func: Function to process each item
            show_progress: Whether to show progress
            
        Returns:
            List of processing results
        """
        results = []
        
        try:
            executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
            
            with executor_class(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_item = {executor.submit(process_func, item): item for item in items}
                
                # Collect results
                for i, future in enumerate(future_to_item):
                    try:
                        result = future.result(timeout=None)
                        results.append(result)
                        
                        if show_progress:
                            self.logger.info(f"Completed {i + 1}/{len(items)} items")
                            
                    except Exception as e:
                        self.logger.error(f"Failed to process item {future_to_item[future]}: {e}")
                        results.append({
                            'success': False,
                            'error': str(e),
                            'item': future_to_item[future]
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Parallel processing failed: {e}")
            # Fallback to sequential processing
            for item in items:
                try:
                    result = process_func(item)
                    results.append(result)
                except Exception as item_error:
                    results.append({
                        'success': False,
                        'error': str(item_error),
                        'item': item
                    })
            
            return results


class PerformanceMonitor:
    """Monitors and reports performance metrics."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.available = PSUTIL_AVAILABLE
    
    def start_monitoring(self) -> Dict[str, Any]:
        """Start performance monitoring."""
        start_info = {
            'start_time': time.time(),
            'available': self.available
        }
        
        if self.available:
            try:
                process = psutil.Process()
                start_info.update({
                    'memory_start_mb': process.memory_info().rss / (1024 * 1024),
                    'cpu_count': psutil.cpu_count(),
                    'cpu_percent_start': process.cpu_percent()
                })
            except Exception as e:
                self.logger.warning(f"Could not start performance monitoring: {e}")
                start_info['available'] = False
        
        return start_info
    
    def end_monitoring(self, start_info: Dict[str, Any], audio_duration: float = 0) -> ProcessingStats:
        """End performance monitoring and calculate stats."""
        end_time = time.time()
        processing_time = end_time - start_info['start_time']
        
        # Default stats
        stats = ProcessingStats(
            start_time=start_info['start_time'],
            end_time=end_time,
            memory_start=start_info.get('memory_start_mb', 0),
            memory_peak=start_info.get('memory_start_mb', 0),
            memory_end=start_info.get('memory_start_mb', 0),
            cpu_usage=0,
            processing_speed=audio_duration / processing_time if processing_time > 0 and audio_duration > 0 else 0
        )
        
        if start_info.get('available') and self.available:
            try:
                process = psutil.Process()
                memory_end = process.memory_info().rss / (1024 * 1024)
                cpu_percent = process.cpu_percent()
                
                stats.memory_end = memory_end
                stats.memory_peak = max(stats.memory_start, memory_end)
                stats.cpu_usage = cpu_percent
                
            except Exception as e:
                self.logger.warning(f"Could not end performance monitoring: {e}")
        
        return stats
    
    def format_performance_report(self, stats: ProcessingStats) -> str:
        """Format performance report as string."""
        report = [
            "Performance Report:",
            f"  Processing Time: {stats.end_time - stats.start_time:.2f}s",
        ]
        
        if stats.processing_speed > 0:
            report.append(f"  Processing Speed: {stats.processing_speed:.2f}x realtime")
        
        if stats.memory_start > 0:
            report.extend([
                f"  Memory Start: {stats.memory_start:.1f} MB",
                f"  Memory Peak: {stats.memory_peak:.1f} MB",
                f"  Memory End: {stats.memory_end:.1f} MB",
                f"  Memory Used: {stats.memory_peak - stats.memory_start:.1f} MB"
            ])
        
        if stats.cpu_usage > 0:
            report.append(f"  CPU Usage: {stats.cpu_usage:.1f}%")
        
        if stats.cache_hits > 0 or stats.cache_misses > 0:
            hit_rate = stats.cache_hits / (stats.cache_hits + stats.cache_misses) * 100
            report.extend([
                f"  Cache Hits: {stats.cache_hits}",
                f"  Cache Misses: {stats.cache_misses}",
                f"  Cache Hit Rate: {hit_rate:.1f}%"
            ])
        
        return "\n".join(report)