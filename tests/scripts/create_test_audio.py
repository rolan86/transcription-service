#!/usr/bin/env python3
"""
Create a simple test audio file for testing transcription
"""

import numpy as np
import wave
import math

def create_test_audio():
    """Create a simple audio file with a tone for testing."""
    
    # Audio parameters
    sample_rate = 16000  # 16kHz
    duration = 3  # 3 seconds
    frequency = 440  # A4 note
    
    # Generate samples
    samples = []
    for i in range(int(sample_rate * duration)):
        time = i / sample_rate
        # Create a simple sine wave that fades out
        amplitude = 0.3 * math.exp(-time)  # Exponential decay
        sample = amplitude * math.sin(2 * math.pi * frequency * time)
        samples.append(sample)
    
    # Convert to 16-bit integers
    samples = np.array(samples)
    samples = (samples * 32767).astype(np.int16)
    
    # Save as WAV file
    filename = "test_audio.wav"
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes = 16 bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    print(f"✅ Created test audio file: {filename}")
    print(f"Duration: {duration} seconds")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Frequency: {frequency} Hz")
    
    return filename

if __name__ == "__main__":
    create_test_audio()