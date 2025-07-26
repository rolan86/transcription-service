# 🧪 Tests

This directory contains test files and scripts for the Professional Transcription Service.

## Structure

```
tests/
├── test_files/          # Test media files (audio/video)
├── scripts/             # Test and utility scripts
├── unit/               # Unit tests (future)
└── integration/        # Integration tests (future)
```

## Test Files

- **test_audio.wav** - Small audio file for basic testing
- **test_video_with_audio.mp4** - Video file for audio extraction testing
- **long_test_with_audio_10min.mp4** - Large file for chunked processing testing
- **TestVidAudio.mp4** - Real demo video for end-to-end testing

## Test Scripts

- **create_test_audio.py** - Generates synthetic audio for testing
- **create_test_video.py** - Creates test video files with audio
- **create_long_test_file.py** - Generates large files for performance testing
- **test_components.py** - Component-level testing script
- **test_large_file_simulation.py** - Large file processing simulation

## Running Tests

```bash
# Basic functionality test
python transcribe transcribe tests/test_files/test_audio.wav

# Video processing test
python transcribe transcribe tests/test_files/test_video_with_audio.mp4

# Large file chunking test
python transcribe transcribe tests/test_files/long_test_with_audio_10min.mp4 --verbose

# Component testing
cd tests/scripts
python test_components.py
```

## Test Coverage

Current test coverage includes:
- ✅ File format validation
- ✅ Audio extraction from video
- ✅ Chunked processing for large files
- ✅ CLI interface functionality
- ✅ Configuration loading
- ✅ Output format generation

Future test additions:
- [ ] Unit tests for individual components
- [ ] Integration tests for full workflows
- [ ] Performance benchmarking
- [ ] Error handling edge cases