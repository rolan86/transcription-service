"""
Advanced audio preprocessing module for Phase 3B.
Provides noise reduction, volume normalization, and audio quality enhancement.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from rich.console import Console

try:
    import librosa
    import soundfile as sf
    import numpy as np
    from scipy import signal
    PREPROCESSING_AVAILABLE = True
    
    # Noisereduce is optional
    try:
        import noisereduce as nr
        NOISEREDUCE_AVAILABLE = True
    except ImportError:
        NOISEREDUCE_AVAILABLE = False
        nr = None
        
except ImportError:
    PREPROCESSING_AVAILABLE = False
    NOISEREDUCE_AVAILABLE = False
    nr = None

console = Console()

class AudioPreprocessor:
    """Handles advanced audio preprocessing features."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.available = PREPROCESSING_AVAILABLE
        
        if not self.available:
            self.logger.warning("Audio preprocessing dependencies not available. "
                              "Install with: pip install librosa soundfile scipy")
        elif not NOISEREDUCE_AVAILABLE:
            self.logger.info("Noise reduction not available. Install with: pip install noisereduce")
    
    def preprocess_audio(self, 
                        audio_path: str,
                        temp_dir: Optional[str] = None,
                        noise_reduction: bool = False,
                        volume_normalization: bool = False,
                        high_pass_filter: bool = False,
                        low_pass_filter: bool = False,
                        target_sample_rate: Optional[int] = None,
                        enhance_speech: bool = False) -> Dict[str, Any]:
        """
        Apply various audio preprocessing techniques.
        
        Args:
            audio_path: Path to input audio file
            temp_dir: Directory for temporary files
            noise_reduction: Apply noise reduction
            volume_normalization: Normalize audio volume
            high_pass_filter: Apply high-pass filter to remove low-frequency noise
            low_pass_filter: Apply low-pass filter to remove high-frequency noise
            target_sample_rate: Resample to target sample rate
            enhance_speech: Apply speech enhancement algorithms
            
        Returns:
            Dictionary with preprocessing results and output file path
        """
        if not self.available:
            return {
                'enabled': False,
                'processed_file': audio_path,
                'error': 'Audio preprocessing dependencies not available',
                'preprocessing_applied': []
            }
        
        try:
            # Create temp directory if not provided
            if temp_dir is None:
                temp_dir = tempfile.gettempdir()
            
            # Load audio file
            self.logger.info(f"Loading audio file: {audio_path}")
            audio, sr = librosa.load(audio_path, sr=None)
            original_sr = sr
            
            preprocessing_applied = []
            processing_stats = {
                'original_sample_rate': original_sr,
                'original_duration': len(audio) / sr,
                'original_rms': float(np.sqrt(np.mean(audio**2)))
            }
            
            # Apply preprocessing steps in order
            
            # 1. Resample if requested
            if target_sample_rate and target_sample_rate != sr:
                self.logger.info(f"Resampling from {sr}Hz to {target_sample_rate}Hz")
                audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sample_rate)
                sr = target_sample_rate
                preprocessing_applied.append('resampling')
                processing_stats['target_sample_rate'] = target_sample_rate
            
            # 2. High-pass filter (remove low-frequency noise like rumble)
            if high_pass_filter:
                self.logger.info("Applying high-pass filter")
                audio = self._apply_high_pass_filter(audio, sr)
                preprocessing_applied.append('high_pass_filter')
            
            # 3. Low-pass filter (remove high-frequency noise)
            if low_pass_filter:
                self.logger.info("Applying low-pass filter")
                audio = self._apply_low_pass_filter(audio, sr)
                preprocessing_applied.append('low_pass_filter')
            
            # 4. Noise reduction
            if noise_reduction:
                if NOISEREDUCE_AVAILABLE:
                    self.logger.info("Applying noise reduction")
                    audio = self._apply_noise_reduction(audio, sr)
                    preprocessing_applied.append('noise_reduction')
                else:
                    self.logger.warning("Noise reduction requested but noisereduce not available")
            
            # 5. Speech enhancement
            if enhance_speech:
                self.logger.info("Applying speech enhancement")
                audio = self._enhance_speech(audio, sr)
                preprocessing_applied.append('speech_enhancement')
            
            # 6. Volume normalization (should be last)
            if volume_normalization:
                self.logger.info("Applying volume normalization")
                audio = self._normalize_volume(audio)
                preprocessing_applied.append('volume_normalization')
            
            # Calculate final stats
            processing_stats.update({
                'final_sample_rate': sr,
                'final_duration': len(audio) / sr,
                'final_rms': float(np.sqrt(np.mean(audio**2))),
                'preprocessing_applied': preprocessing_applied
            })
            
            # Save processed audio to temporary file
            temp_file_path = self._save_processed_audio(audio, sr, audio_path, temp_dir)
            
            return {
                'enabled': True,
                'processed_file': temp_file_path,
                'original_file': audio_path,
                'preprocessing_applied': preprocessing_applied,
                'processing_stats': processing_stats,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Audio preprocessing failed: {str(e)}")
            return {
                'enabled': True,
                'processed_file': audio_path,  # Return original on failure
                'error': str(e),
                'preprocessing_applied': [],
                'success': False
            }
    
    def _apply_high_pass_filter(self, audio: np.ndarray, sr: int, cutoff: float = 80.0) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise."""
        # Butterworth high-pass filter
        nyquist = sr / 2
        normalized_cutoff = cutoff / nyquist
        b, a = signal.butter(4, normalized_cutoff, btype='high')
        return signal.filtfilt(b, a, audio)
    
    def _apply_low_pass_filter(self, audio: np.ndarray, sr: int, cutoff: float = 8000.0) -> np.ndarray:
        """Apply low-pass filter to remove high-frequency noise."""
        # Butterworth low-pass filter
        nyquist = sr / 2
        normalized_cutoff = min(cutoff, nyquist * 0.99) / nyquist
        b, a = signal.butter(4, normalized_cutoff, btype='low')
        return signal.filtfilt(b, a, audio)
    
    def _apply_noise_reduction(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Apply spectral noise reduction."""
        if not NOISEREDUCE_AVAILABLE:
            self.logger.warning("Noise reduction not available, skipping")
            return audio
            
        try:
            # Use noisereduce library for spectral noise reduction
            return nr.reduce_noise(y=audio, sr=sr, stationary=False, prop_decrease=0.8)
        except Exception as e:
            self.logger.warning(f"Noise reduction failed, skipping: {str(e)}")
            return audio
    
    def _enhance_speech(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Apply speech enhancement techniques."""
        try:
            # Apply spectral subtraction and dynamic range compression
            
            # 1. Spectral subtraction (simple implementation)
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Estimate noise from first 0.5 seconds
            noise_frames = int(0.5 * sr / 512)  # 512 is default hop_length
            noise_magnitude = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
            
            # Subtract noise with over-subtraction factor
            alpha = 2.0  # Over-subtraction factor
            enhanced_magnitude = magnitude - alpha * noise_magnitude
            
            # Ensure magnitude doesn't go negative
            enhanced_magnitude = np.maximum(enhanced_magnitude, 0.1 * magnitude)
            
            # Reconstruct signal
            enhanced_stft = enhanced_magnitude * np.exp(1j * phase)
            enhanced_audio = librosa.istft(enhanced_stft)
            
            # 2. Dynamic range compression
            # Apply soft compression to enhance speech clarity
            threshold = 0.1
            ratio = 4.0
            
            # Find samples above threshold
            above_threshold = np.abs(enhanced_audio) > threshold
            
            # Apply compression
            compressed_audio = enhanced_audio.copy()
            compressed_audio[above_threshold] = (
                np.sign(enhanced_audio[above_threshold]) * 
                (threshold + (np.abs(enhanced_audio[above_threshold]) - threshold) / ratio)
            )
            
            return compressed_audio
            
        except Exception as e:
            self.logger.warning(f"Speech enhancement failed, skipping: {str(e)}")
            return audio
    
    def _normalize_volume(self, audio: np.ndarray, target_level: float = -20.0) -> np.ndarray:
        """Normalize audio volume to target dB level."""
        # Calculate RMS
        rms = np.sqrt(np.mean(audio**2))
        
        if rms == 0:
            return audio
        
        # Calculate target RMS from dB
        target_rms = 10**(target_level / 20.0)
        
        # Calculate gain
        gain = target_rms / rms
        
        # Apply gain with soft limiting
        normalized = audio * gain
        
        # Soft limiting to prevent clipping
        limit_threshold = 0.95
        above_limit = np.abs(normalized) > limit_threshold
        normalized[above_limit] = (
            np.sign(normalized[above_limit]) * 
            (limit_threshold + (np.abs(normalized[above_limit]) - limit_threshold) * 0.1)
        )
        
        return normalized
    
    def _save_processed_audio(self, audio: np.ndarray, sr: int, original_path: str, temp_dir: str) -> str:
        """Save processed audio to temporary file."""
        # Generate temporary filename
        original_name = Path(original_path).stem
        temp_filename = f"processed_{original_name}_{hash(str(audio.tobytes())) % 10000}.wav"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # Save audio file
        sf.write(temp_path, audio, sr)
        
        self.logger.info(f"Processed audio saved to: {temp_path}")
        return temp_path


class AudioAnalyzer:
    """Analyze audio quality and recommend preprocessing options."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.available = PREPROCESSING_AVAILABLE
    
    def analyze_audio_quality(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio quality and recommend preprocessing options.
        
        Returns:
            Dictionary with quality metrics and recommendations
        """
        if not self.available:
            return {
                'available': False,
                'error': 'Audio analysis dependencies not available'
            }
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=None)
            
            # Calculate quality metrics
            metrics = {
                'sample_rate': sr,
                'duration': len(audio) / sr,
                'rms_level': float(np.sqrt(np.mean(audio**2))),
                'peak_level': float(np.max(np.abs(audio))),
                'dynamic_range': float(np.max(audio) - np.min(audio)),
                'zero_crossing_rate': float(np.mean(librosa.feature.zero_crossing_rate(audio))),
                'spectral_centroid': float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr))),
                'spectral_rolloff': float(np.mean(librosa.feature.spectral_rolloff(y=audio, sr=sr)))
            }
            
            # Calculate SNR estimate
            # Use first and last 0.5 seconds as potential noise segments
            noise_duration = min(0.5, len(audio) / sr / 4)
            noise_samples = int(noise_duration * sr)
            
            if noise_samples > 0:
                noise_start = audio[:noise_samples]
                noise_end = audio[-noise_samples:]
                noise_estimate = np.mean([np.var(noise_start), np.var(noise_end)])
                signal_power = np.var(audio)
                
                if noise_estimate > 0:
                    snr_db = 10 * np.log10(signal_power / noise_estimate)
                    metrics['estimated_snr_db'] = float(snr_db)
                else:
                    metrics['estimated_snr_db'] = float('inf')
            else:
                metrics['estimated_snr_db'] = None
            
            # Generate recommendations
            recommendations = self._generate_recommendations(metrics)
            
            return {
                'available': True,
                'metrics': metrics,
                'recommendations': recommendations,
                'quality_score': self._calculate_quality_score(metrics),
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Audio quality analysis failed: {str(e)}")
            return {
                'available': True,
                'error': str(e),
                'success': False
            }
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate preprocessing recommendations based on audio metrics."""
        recommendations = {
            'noise_reduction': False,
            'volume_normalization': False,
            'high_pass_filter': False,
            'low_pass_filter': False,
            'enhance_speech': False,
            'resample': False,
            'reasons': []
        }
        
        # Check for low volume
        if metrics['rms_level'] < 0.01:  # Very quiet audio
            recommendations['volume_normalization'] = True
            recommendations['reasons'].append("Low audio level detected")
        
        # Check for high volume/clipping
        if metrics['peak_level'] > 0.95:
            recommendations['volume_normalization'] = True
            recommendations['reasons'].append("Potential clipping detected")
        
        # Check SNR for noise reduction
        if metrics.get('estimated_snr_db') and metrics['estimated_snr_db'] < 15:
            recommendations['noise_reduction'] = True
            recommendations['enhance_speech'] = True
            recommendations['reasons'].append("Low signal-to-noise ratio detected")
        
        # Check sample rate
        if metrics['sample_rate'] < 16000:
            recommendations['resample'] = True
            recommendations['reasons'].append("Low sample rate may affect transcription quality")
        elif metrics['sample_rate'] > 48000:
            recommendations['resample'] = True
            recommendations['reasons'].append("High sample rate - resampling can improve processing speed")
        
        # Check for potential low-frequency noise
        if metrics['spectral_centroid'] < 500:  # Very low spectral centroid
            recommendations['high_pass_filter'] = True
            recommendations['reasons'].append("Low-frequency content detected (possible rumble/noise)")
        
        # Check zero crossing rate (indicator of noise)
        if metrics['zero_crossing_rate'] > 0.3:
            recommendations['noise_reduction'] = True
            recommendations['reasons'].append("High zero-crossing rate indicates noise")
        
        return recommendations
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall audio quality score (0-100)."""
        score = 100.0
        
        # Penalize low volume
        if metrics['rms_level'] < 0.001:
            score -= 30
        elif metrics['rms_level'] < 0.01:
            score -= 15
        
        # Penalize clipping
        if metrics['peak_level'] > 0.95:
            score -= 25
        
        # Penalize low SNR
        if metrics.get('estimated_snr_db'):
            if metrics['estimated_snr_db'] < 10:
                score -= 30
            elif metrics['estimated_snr_db'] < 20:
                score -= 15
        
        # Penalize very low sample rate
        if metrics['sample_rate'] < 8000:
            score -= 40
        elif metrics['sample_rate'] < 16000:
            score -= 20
        
        # Penalize high noise indicators
        if metrics['zero_crossing_rate'] > 0.3:
            score -= 20
        
        return max(0.0, score)