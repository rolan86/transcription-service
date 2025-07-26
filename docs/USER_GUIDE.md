# 📚 User Guide

Complete guide to using the Professional Transcription Service for all your audio and video transcription needs.

## Table of Contents
- [Getting Started](#getting-started)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [File Formats](#file-formats)
- [Output Options](#output-options)
- [Large File Processing](#large-file-processing)
- [Batch Processing](#batch-processing)
- [Configuration](#configuration)
- [Tips & Best Practices](#tips--best-practices)

## Getting Started

### First Transcription
After installation, try your first transcription:

```bash
# Transcribe an audio file
python transcribe transcribe your_audio.mp3
```

That's it! The transcription will be saved as `your_audio.txt` in the same directory.

### Understanding the Interface
The CLI uses a command structure:
```bash
python transcribe [COMMAND] [OPTIONS] [ARGUMENTS]
```

Main commands:
- `transcribe` - Process a single file
- `batch` - Process multiple files
- `config` - Manage settings
- `version` - Show version info

## Basic Usage

### Single File Transcription

#### Audio Files
```bash
# Basic transcription
python transcribe transcribe audio.mp3

# Specify output file
python transcribe transcribe audio.mp3 --output my_transcript.txt

# Choose output format
python transcribe transcribe audio.mp3 --format json
```

#### Video Files
```bash
# Transcribe video (audio will be extracted automatically)
python transcribe transcribe video.mp4

# Specify model for better accuracy
python transcribe transcribe interview.mp4 --model large
```

### Common Options

#### Model Selection
```bash
# Use tiny model (fastest, least accurate)
python transcribe transcribe file.mp3 --model tiny

# Use base model (default, good balance)
python transcribe transcribe file.mp3 --model base

# Use large model (slowest, most accurate)
python transcribe transcribe file.mp3 --model large
```

#### Language Specification
```bash
# Auto-detect language (default)
python transcribe transcribe file.mp3

# Specify language for better accuracy
python transcribe transcribe spanish.mp3 --language es
python transcribe transcribe french.mp4 --language fr
```

#### Include Timestamps
```bash
# Add timestamps to output
python transcribe transcribe meeting.mp4 --timestamps

# Timestamps in JSON format provide more detail
python transcribe transcribe meeting.mp4 --timestamps --format json
```

## Advanced Features

### Custom Output Paths
```bash
# Specify exact output file
python transcribe transcribe input.mp3 --output /path/to/transcript.txt

# Output to different directory
python transcribe transcribe input.mp3 --output ../transcripts/result.txt
```

### Verbose and Quiet Modes
```bash
# Verbose output (more details)
python transcribe transcribe file.mp3 --verbose

# Quiet mode (minimal output)
python transcribe transcribe file.mp3 --quiet
```

### Configuration Files
```bash
# Use specific config file
python transcribe transcribe file.mp3 --config /path/to/config.yaml
```

## File Formats

### Supported Audio Formats
- **MP3** - Most common, widely supported
- **WAV** - Uncompressed, highest quality
- **FLAC** - Lossless compression
- **M4A** - Apple's format, good quality

### Supported Video Formats
- **MP4** - Most common video format
- **MOV** - Apple's video format
- **AVI** - Windows video format

### Format Examples
```bash
# Audio formats
python transcribe transcribe podcast.mp3
python transcribe transcribe recording.wav
python transcribe transcribe music.flac
python transcribe transcribe audiobook.m4a

# Video formats (audio will be extracted)
python transcribe transcribe lecture.mp4
python transcribe transcribe presentation.mov
python transcribe transcribe meeting.avi
```

## Output Options

### Text Format (Default)
Clean, readable text with optional metadata header:

```bash
python transcribe transcribe file.mp3 --format txt
```

**Example output:**
```
# Transcription
# File: meeting.mp3
# Generated: 2025-01-20T10:30:00
# Model: base
# Language: en
# Processing time: 45.67s
# Confidence: 89.2%

==================================================

Welcome to today's team meeting. Let's start by reviewing 
our progress on the quarterly objectives...
```

### JSON Format
Structured data with detailed metadata:

```bash
python transcribe transcribe file.mp3 --format json
```

**Example output:**
```json
{
  "metadata": {
    "timestamp": "2025-01-20T10:30:00",
    "input_file": {
      "name": "meeting.mp3",
      "size_mb": 15.3
    },
    "transcription": {
      "model": "base",
      "language": "en",
      "confidence": 0.892
    }
  },
  "transcription": {
    "text": "Welcome to today's team meeting...",
    "word_count": 234
  },
  "segments": [
    {
      "start": 0.0,
      "end": 4.5,
      "text": "Welcome to today's team meeting.",
      "confidence": 0.95
    }
  ]
}
```

### With Timestamps
```bash
# Text with timestamps
python transcribe transcribe file.mp3 --timestamps

# JSON with detailed timing
python transcribe transcribe file.mp3 --timestamps --format json
```

## Large File Processing

The service automatically handles large files using chunked processing.

### Automatic Chunking
Files longer than 5 minutes are automatically processed in chunks:

```bash
# Large file - automatic chunking
python transcribe transcribe long_lecture.mp4
```

**Output:**
```
📦 Using chunked processing for large file
📦 Creating 24 chunks (30s each) from 720.0s file
✅ Created 24 chunks
📊 Total audio size: 220.8 MB
🎙️ Transcribing chunks: 100%|██████| 24/24 [05:23<00:00, 2.15chunk/s]
✅ Chunked processing completed!
```

### Force Chunking
Force chunking for any file:

```bash
python transcribe transcribe any_file.mp3 --force-chunking
```

### Custom Chunk Duration
Adjust chunk size (default: 30 seconds):

```bash
# Use 60-second chunks
python transcribe transcribe large_file.mp4 --chunk-duration 60

# Use 15-second chunks for very large files
python transcribe transcribe huge_file.mp4 --chunk-duration 15
```

### Large File Benefits
- **Memory Efficient**: Constant memory usage regardless of file size
- **Progress Tracking**: Real-time progress with time estimates
- **Fault Tolerant**: Individual chunk failures don't stop processing
- **Resume Capable**: Can handle interruptions gracefully

## Batch Processing

Process multiple files at once.

### Basic Batch Processing
```bash
# Process all files in a directory
python transcribe batch recordings/

# Specify output directory
python transcribe batch audio_files/ --output-dir transcripts/
```

### Recursive Processing
```bash
# Process files in subdirectories too
python transcribe batch media/ --recursive
```

### Batch with Options
```bash
# Batch process with specific settings
python transcribe batch interviews/ \
    --format json \
    --model large \
    --timestamps \
    --language en
```

### Batch Output
```
📁 Batch Transcription
📂 Input directory: recordings/
📝 Format: TXT
🤖 Model: base
🔄 Recursive: No

INFO transcription: Processing example1.mp3 (1/5, 20.0%)
✅ example1.mp3 - 12.34s
INFO transcription: Processing example2.wav (2/5, 40.0%)
✅ example2.wav - 8.91s
...
✅ Batch transcription completed!
📊 Processed: 5/5 files
⏱️  Total time: 45.67s
```

## Configuration

### View Current Configuration
```bash
python transcribe config --show-config
```

### Configuration File Location
```bash
python transcribe config --config-path
```

### Configuration Hierarchy
Settings are loaded in this order (highest priority first):
1. Command-line arguments
2. Environment variables
3. User config file (`~/.transcription/config.yaml`)
4. System config file
5. Built-in defaults

### Example User Configuration
Create `~/.transcription/config.yaml`:

```yaml
transcription:
  default_model: "base"
  default_language: "en"
  chunk_duration: 30
  
output:
  default_format: "txt"
  include_metadata: true
  include_timestamps: false
  
processing:
  cleanup_temp_files: true
  progress_reporting: true
  
logging:
  level: "INFO"
```

### Environment Variables
```bash
# Set default model
export TRANSCRIPTION_MODEL="large"

# Set default language
export TRANSCRIPTION_LANGUAGE="en"

# Set output format
export TRANSCRIPTION_OUTPUT_FORMAT="json"
```

## Tips & Best Practices

### Choosing the Right Model

#### For Speed (Real-time or faster)
```bash
python transcribe transcribe file.mp3 --model tiny
```
- Use for: Quick tests, real-time processing
- Accuracy: ~80-85%
- Speed: 2-5x realtime

#### For Balance (Recommended)
```bash
python transcribe transcribe file.mp3 --model base
```
- Use for: Most general-purpose transcription
- Accuracy: ~85-90%
- Speed: 1-2x realtime

#### For Accuracy
```bash
python transcribe transcribe file.mp3 --model large
```
- Use for: Critical transcriptions, professional use
- Accuracy: ~95-99%
- Speed: 0.5-1x realtime

### Improving Accuracy

#### Specify Language
```bash
# Much better accuracy when language is known
python transcribe transcribe spanish.mp3 --language es
```

#### Use Better Audio Quality
- **WAV/FLAC** formats are better than MP3
- **16kHz+ sample rate** recommended
- **Mono audio** is sufficient and faster
- **Reduce background noise** before transcription

#### Choose Appropriate Model
```bash
# For technical content, use larger models
python transcribe transcribe technical_talk.mp4 --model large
```

### Performance Optimization

#### For Large Files
```bash
# Reduce chunk size for very large files
python transcribe transcribe huge_file.mp4 --chunk-duration 15

# Use smaller model for speed
python transcribe transcribe large_file.mp4 --model base
```

#### For Batch Processing
```bash
# Process in batches with appropriate model
python transcribe batch recordings/ --model base --format txt
```

### File Organization

#### Organized Output
```bash
# Create organized output structure
mkdir -p transcripts/{txt,json}

# Process with organized output
python transcribe transcribe meeting.mp4 --output transcripts/txt/meeting.txt
python transcribe transcribe meeting.mp4 --output transcripts/json/meeting.json --format json
```

#### Batch Organization
```bash
# Batch process with organized output
python transcribe batch recordings/ --output-dir transcripts/ --recursive
```

### Common Workflows

#### Podcast Transcription
```bash
# High accuracy for podcast episodes
python transcribe transcribe podcast_episode.mp3 \
    --model large \
    --language en \
    --format json \
    --timestamps
```

#### Meeting Transcription
```bash
# Quick meeting notes
python transcribe transcribe meeting.mp4 \
    --model base \
    --format txt \
    --output meeting_notes.txt
```

#### Interview Processing
```bash
# Batch process interview recordings
python transcribe batch interviews/ \
    --model large \
    --format json \
    --timestamps \
    --output-dir transcripts/
```

#### Academic Research
```bash
# Process lecture recordings with high accuracy
python transcribe transcribe lecture.mp4 \
    --model large \
    --language en \
    --timestamps \
    --format json \
    --output research/lecture_01.json
```

## Troubleshooting Common Issues

### File Not Processing
```bash
# Check file format
file your_audio.mp3

# Test with different model
python transcribe transcribe file.mp3 --model tiny
```

### Poor Accuracy
```bash
# Specify language
python transcribe transcribe file.mp3 --language en

# Use larger model
python transcribe transcribe file.mp3 --model large

# Check audio quality
ffprobe -v quiet -show_format -show_streams file.mp3
```

### Slow Processing
```bash
# Use smaller model
python transcribe transcribe file.mp3 --model tiny

# Enable chunking for large files
python transcribe transcribe file.mp3 --force-chunking
```

### Memory Issues
```bash
# Use tiny model
python transcribe transcribe file.mp3 --model tiny

# Force chunking
python transcribe transcribe file.mp3 --force-chunking --chunk-duration 15
```

## Getting Help

### Built-in Help
```bash
# General help
python transcribe --help

# Command-specific help
python transcribe transcribe --help
python transcribe batch --help
```

### Verbose Output
```bash
# See detailed processing information
python transcribe transcribe file.mp3 --verbose
```

### Configuration Check
```bash
# Verify your settings
python transcribe config --show-config
```

For more help, see the [Troubleshooting Guide](TROUBLESHOOTING.md) or create an issue on GitHub.