#!/usr/bin/env python3
"""
Create a longer test file to properly test chunked processing
"""

import ffmpeg
import numpy as np
import wave
import os
import tempfile

def create_long_test_audio(duration_minutes=10):
    """Create a test audio file with varying tones to simulate speech patterns."""
    
    sample_rate = 16000
    duration_seconds = duration_minutes * 60
    
    print(f"🔧 Creating {duration_minutes}-minute test audio file...")
    
    # Create different tone patterns to simulate variety
    samples = []
    frequencies = [220, 440, 660, 880]  # Different frequencies
    
    for i in range(int(sample_rate * duration_seconds)):
        time = i / sample_rate
        
        # Change frequency every 30 seconds to simulate different "speech" patterns
        freq_index = int(time // 30) % len(frequencies)
        frequency = frequencies[freq_index]
        
        # Create amplitude variation to simulate speech patterns
        amplitude = 0.2 * (1 + 0.5 * np.sin(2 * np.pi * 0.1 * time))  # Slow amplitude modulation
        
        # Add some "silence" periods
        if int(time) % 60 < 50:  # 50 seconds of tone, 10 seconds of silence each minute
            sample = amplitude * np.sin(2 * np.pi * frequency * time)
        else:
            sample = 0  # Silence
            
        samples.append(sample)
    
    # Convert to 16-bit integers
    samples = np.array(samples)
    samples = (samples * 32767).astype(np.int16)
    
    # Save as WAV file
    filename = f"long_test_audio_{duration_minutes}min.wav"
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes = 16 bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    file_size_mb = os.path.getsize(filename) / (1024 * 1024)
    
    print(f"✅ Created: {filename}")
    print(f"📏 Duration: {duration_minutes} minutes ({duration_seconds} seconds)")
    print(f"📊 File size: {file_size_mb:.1f} MB")
    print(f"🎵 Pattern: Varying tones with silence breaks")
    
    return filename

def create_long_test_video(duration_minutes=10):
    """Create a test video file with the long audio."""
    
    # First create the audio
    audio_file = create_long_test_audio(duration_minutes)
    
    try:
        video_file = f"long_test_video_{duration_minutes}min.mp4"
        duration_seconds = duration_minutes * 60
        
        print(f"🎬 Creating {duration_minutes}-minute test video...")
        
        # Create video with changing colors to make it interesting
        color_input = f'color=black:size=320x240:rate=1:duration={duration_seconds}'
        
        # Create simple video and add the audio
        (
            ffmpeg
            .input(color_input, f='lavfi')
            .output(
                video_file,
                vcodec='libx264',
                pix_fmt='yuv420p',
                r=1  # 1 fps for efficiency
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        
        # Add audio to video
        video_input = ffmpeg.input(video_file)
        audio_input = ffmpeg.input(audio_file)
        
        final_video = f"long_test_with_audio_{duration_minutes}min.mp4"
        
        (
            ffmpeg
            .output(
                video_input['v'], 
                audio_input['a'], 
                final_video,
                vcodec='copy',
                acodec='aac',
                shortest=None
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        
        # Cleanup intermediate files
        for temp_file in [audio_file, video_file]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        file_size_mb = os.path.getsize(final_video) / (1024 * 1024)
        
        print(f"✅ Created: {final_video}")
        print(f"📏 Duration: {duration_minutes} minutes")
        print(f"📊 File size: {file_size_mb:.1f} MB")
        print(f"🎬 Video: 320x240 @ 1fps with varying audio patterns")
        
        return final_video
        
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        return None
    except Exception as e:
        print(f"❌ Error creating video: {str(e)}")
        return None

if __name__ == "__main__":
    print("🧪 Creating Long Test Files for Chunked Processing")
    print("=" * 60)
    
    # Create a 10-minute test file (this should trigger chunking)
    video_file = create_long_test_video(10)
    
    if video_file:
        print(f"\n🎯 Test file ready: {video_file}")
        print(f"📦 Expected chunks: ~20 (30-second chunks)")
        print(f"🧪 This file will test real chunked processing!")
    else:
        print("❌ Failed to create test file")