"""
URL downloader for YouTube and Vimeo videos.
Uses yt-dlp to download audio for transcription.
"""

import os
import tempfile
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse


class URLDownloader:
    """
    Downloads audio from video URLs using yt-dlp.
    Supports YouTube and Vimeo.
    """

    SUPPORTED_DOMAINS = {
        'youtube.com',
        'www.youtube.com',
        'youtu.be',
        'vimeo.com',
        'www.vimeo.com',
    }

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize URL downloader.

        Args:
            output_dir: Directory for downloaded files (default: temp dir)
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        self._yt_dlp = None

    @property
    def yt_dlp(self):
        """Lazy import of yt-dlp."""
        if self._yt_dlp is None:
            try:
                import yt_dlp
                self._yt_dlp = yt_dlp
            except ImportError:
                raise ImportError(
                    "yt-dlp is required for URL downloads. "
                    "Install with: pip install yt-dlp"
                )
        return self._yt_dlp

    def is_supported_url(self, url: str) -> bool:
        """
        Check if URL is from a supported domain.

        Args:
            url: URL to check

        Returns:
            True if supported
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return domain in self.SUPPORTED_DOMAINS
        except Exception:
            return False

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about a video without downloading.

        Args:
            url: Video URL

        Returns:
            Dictionary with video information
        """
        if not self.is_supported_url(url):
            return {
                'success': False,
                'error': 'Unsupported URL. Only YouTube and Vimeo are supported.',
            }

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        try:
            with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail'),
                    'description': info.get('description', '')[:200],
                    'id': info.get('id'),
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get video info: {str(e)}',
            }

    def download_audio(
        self,
        url: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Download audio from a video URL.

        Args:
            url: Video URL
            progress_callback: Optional callback(progress, status) for updates

        Returns:
            Dictionary with download result
        """
        if not self.is_supported_url(url):
            return {
                'success': False,
                'error': 'Unsupported URL. Only YouTube and Vimeo are supported.',
            }

        # Generate unique filename
        temp_path = os.path.join(self.output_dir, f'url_download_{os.getpid()}')

        def progress_hook(d):
            if progress_callback:
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        percent = (downloaded / total) * 100
                        progress_callback(percent / 100, 'Downloading...')
                elif d['status'] == 'finished':
                    progress_callback(1.0, 'Download complete, extracting audio...')

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'outtmpl': temp_path,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
        }

        try:
            with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # Find the output file
                output_file = temp_path + '.wav'
                if not os.path.exists(output_file):
                    # Try without extension
                    for ext in ['.wav', '.m4a', '.mp3', '.webm']:
                        candidate = temp_path + ext
                        if os.path.exists(candidate):
                            output_file = candidate
                            break

                if not os.path.exists(output_file):
                    return {
                        'success': False,
                        'error': 'Download completed but audio file not found',
                    }

                return {
                    'success': True,
                    'file_path': output_file,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'filename': self._sanitize_filename(info.get('title', 'download')) + '.wav',
                }

        except Exception as e:
            error_msg = str(e)
            # Clean up common error messages
            if 'Video unavailable' in error_msg:
                error_msg = 'Video is unavailable or private'
            elif 'Sign in' in error_msg:
                error_msg = 'Video requires authentication'
            elif 'age' in error_msg.lower():
                error_msg = 'Video is age-restricted'

            return {
                'success': False,
                'error': f'Download failed: {error_msg}',
            }

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename."""
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Limit length
        return name[:100]

    def cleanup(self, file_path: str) -> None:
        """
        Clean up downloaded file.

        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass
