#!/usr/bin/env python3
"""
Create a simple test video file for testing MP4 processing
"""

import ffmpeg
import numpy as np
import wave
import os

def create_test_video():
    """Create a simple test video with audio track."""
    
    # First create a simple audio file
    sample_rate = 16000
    duration = 2  # 2 seconds
    frequency = 440  # A4 note
    
    # Generate audio samples
    samples = []
    for i in range(int(sample_rate * duration)):
        time = i / sample_rate
        amplitude = 0.3 * np.sin(2 * np.pi * frequency * time)
        samples.append(amplitude)
    
    # Convert to 16-bit integers
    samples = np.array(samples)
    samples = (samples * 32767).astype(np.int16)
    
    # Save as temporary WAV file
    temp_audio = "temp_audio.wav"
    with wave.open(temp_audio, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    # Create a simple video with this audio
    output_file = "test_video.mp4"
    
    try:
        # Create a simple video (black frame) with the audio
        (
            ffmpeg
            .input('color=black:size=320x240:rate=1', f='lavfi', t=duration)
            .output(
                output_file,
                vcodec='libx264',
                acodec='aac',
                pix_fmt='yuv420p'
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # Add audio to the video
        video_input = ffmpeg.input(output_file)
        audio_input = ffmpeg.input(temp_audio)
        
        (
            ffmpeg
            .output(
                video_input['v'], 
                audio_input['a'], 
                'test_video_with_audio.mp4',
                vcodec='copy',
                acodec='aac',
                shortest=None
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # Clean up
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        if os.path.exists(output_file):
            os.remove(output_file)
        
        final_file = 'test_video_with_audio.mp4'    
        print(f"✅ Created test video file: {final_file}")
        print(f"Duration: {duration} seconds")
        print(f"Video: 320x240 black frame")
        print(f"Audio: {frequency}Hz tone")
        
        return final_file
        
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        return None
    except Exception as e:
        print(f"❌ Error creating video: {str(e)}")
        return None
    finally:
        # Cleanup temporary files
        for temp_file in [temp_audio, output_file]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

if __name__ == "__main__":
    create_test_video()