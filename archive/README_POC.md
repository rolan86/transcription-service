# Transcription Service POC

## Overview
Proof of Concept for audio/video transcription service supporting MP3, WAV, and MP4 files.

## Features
- ✅ Audio transcription (MP3, WAV)
- ✅ Video transcription (MP4 with audio extraction)
- ✅ Multiple Whisper model sizes
- ✅ Timestamp support
- ✅ Language detection/specification
- ✅ Confidence scoring

## Installation

### Prerequisites
- Python 3.11+
- FFmpeg (for video processing)

#### Install FFmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
# Audio file transcription
python src/poc/transcribe_poc.py audio.mp3

# Video file transcription (extracts audio automatically)
python src/poc/transcribe_poc.py video.mp4
```

### Advanced Options
```bash
# Use different model size
python src/poc/transcribe_poc.py audio.wav --model small

# Include timestamps
python src/poc/transcribe_poc.py video.mp4 --timestamps

# Specify language
python src/poc/transcribe_poc.py recording.mp3 --language en

# Combined options
python src/poc/transcribe_poc.py presentation.mp4 --model medium --timestamps --language en
```

### Model Sizes
- `tiny`: Fastest, least accurate (~1GB VRAM)
- `base`: Good balance (default) (~1GB VRAM)
- `small`: Better accuracy (~2GB VRAM)
- `medium`: High accuracy (~5GB VRAM)
- `large`: Best accuracy (~10GB VRAM)

## Project Structure
```
src/poc/
├── transcribe_poc.py      # Main POC script
├── file_handler.py        # File validation and format detection
├── audio_processor.py     # Audio extraction and preprocessing
└── transcription_engine.py # Whisper transcription engine
```

## Sample Output
```
============================================================
🎙️  POC TRANSCRIPTION SERVICE
============================================================
1️⃣  Validating input file...
✅ File is valid
📁 File: sample.mp4
📏 Size: 15.3 MB
🎵 Type: video
📍 Path: /path/to/sample.mp4

2️⃣  Processing audio...
✅ Audio preprocessed successfully
⏱️  Duration: 03:45 (225.0s)
🔊 Channels: 1
📊 Sample Rate: 16000 Hz

3️⃣  Transcribing audio...
🤖 Model: base on cpu
Loading Whisper model 'base' on cpu...
Model loaded successfully in 2.34 seconds
Transcribing audio: /tmp/tmp_audio.wav

✅ Transcription completed successfully!
🌍 Language: en
⏱️  Processing time: 45.2s
📊 Confidence: 89.2%
📝 Word count: 234
🔢 Segments: 12

============================================================
📄 TRANSCRIPT:
============================================================
Welcome to this demonstration of our transcription service...
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   ```
   Error: FFmpeg not installed
   Solution: Install FFmpeg using the instructions above
   ```

2. **Out of memory**
   ```
   Error: CUDA out of memory
   Solution: Use a smaller model (--model tiny or --model base)
   ```

3. **File format not supported**
   ```
   Error: Unsupported format
   Solution: Convert to MP3, WAV, or MP4
   ```

## Next Steps (MVP Phase)
- CLI interface with Click
- File output options
- Batch processing
- Additional format support (FLAC, M4A, MOV, AVI)
- Configuration management
- Better error handling