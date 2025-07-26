"""
Enhanced logging system for the transcription service.
Provides colorized console output and optional file logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import colorlog

def setup_logger(name: str = 'transcription', 
                level: str = 'INFO',
                log_file: Optional[str] = None,
                format_string: Optional[str] = None) -> logging.Logger:
    """
    Set up enhanced logger with color support.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        format_string: Custom format string
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = colorlog.StreamHandler(sys.stdout)
    console_formatter = colorlog.ColoredFormatter(
        fmt=format_string or '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            # Ensure log directory exists
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                fmt=format_string or '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logging to {log_file}: {e}")
    
    return logger


class ProgressLogger:
    """Enhanced progress logging for transcription operations."""
    
    def __init__(self, logger: logging.Logger, quiet: bool = False):
        self.logger = logger
        self.quiet = quiet
    
    def info(self, message: str):
        """Log info message if not in quiet mode."""
        if not self.quiet:
            self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def progress(self, message: str, current: int, total: int):
        """Log progress update."""
        if not self.quiet:
            percentage = (current / total) * 100 if total > 0 else 0
            self.logger.info(f"{message} ({current}/{total}, {percentage:.1f}%)")
    
    def file_processed(self, filename: str, duration: float, success: bool):
        """Log file processing result."""
        status = "✅" if success else "❌"
        self.info(f"{status} {filename} - {duration:.2f}s")
    
    def batch_summary(self, processed: int, total: int, total_time: float):
        """Log batch processing summary."""
        success_rate = (processed / total) * 100 if total > 0 else 0
        self.info(f"📊 Batch complete: {processed}/{total} files ({success_rate:.1f}%) in {total_time:.2f}s")