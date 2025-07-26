# ⚡ Quick Start Guide

Get up and running with the Professional Transcription Service in 5 minutes.

## 🚀 5-Minute Setup

### Step 1: Install Prerequisites (2 minutes)

#### macOS
```bash
brew install ffmpeg python@3.11
```

#### Ubuntu/Debian
```bash
sudo apt update && sudo apt install ffmpeg python3.11 python3.11-venv
```

#### Windows
```bash
# Install via Chocolatey (run as Administrator)
choco install ffmpeg python311
```

### Step 2: Set Up Project (2 minutes)

```bash
# Navigate to project directory
cd transcription-service

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Test Installation (1 minute)

```bash
# Verify installation
python transcribe --help

# Should show the welcome screen
```

## 🎯 First Transcription

### Test with Your Audio/Video File
```bash
# Replace 'your_file' with your actual file
python transcribe transcribe your_file.mp3
```

### Expected Output
```
🎙️  Transcription Service
📁 Input: your_file.mp3
📝 Format: TXT
🤖 Model: base

INFO transcription: 🎙️ Starting transcription of your_file.mp3
INFO transcription: 📁 File: your_file.mp3 (5.2 MB)
INFO transcription: 🔄 Using standard processing
Loading Whisper model 'base' on cpu...
✅ Transcription completed successfully!
📄 Output: your_file.txt
⏱️  Processing time: 12.34s
📊 Confidence: 89.2%
```

Your transcript will be saved as `your_file.txt` in the same directory.

## 📋 Essential Commands

### Basic Transcription
```bash
# Audio file
python transcribe transcribe audio.mp3

# Video file (audio extracted automatically)
python transcribe transcribe video.mp4

# With specific output file
python transcribe transcribe input.mp3 --output transcript.txt
```

### Different Models
```bash
# Fast but less accurate
python transcribe transcribe file.mp3 --model tiny

# Default (good balance)
python transcribe transcribe file.mp3 --model base

# Slow but most accurate
python transcribe transcribe file.mp3 --model large
```

### JSON Output
```bash
# Structured output with metadata
python transcribe transcribe file.mp3 --format json
```

### Large Files
```bash
# Automatic chunking for files >5 minutes
python transcribe transcribe long_video.mp4

# Force chunking for any file
python transcribe transcribe any_file.mp3 --force-chunking
```

### Batch Processing
```bash
# Process all files in a directory
python transcribe batch recordings/

# With custom output directory
python transcribe batch audio_files/ --output-dir transcripts/
```

## 🛠️ Quick Troubleshooting

### Common Issues & Solutions

#### "FFmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Windows
choco install ffmpeg
```

#### "Python 3.11 not found"
```bash
# Check available Python versions
python3 --version
python3.11 --version

# Use available version
python3 -m venv venv  # If 3.11 is default
```

#### "Permission denied"
```bash
# Make script executable
chmod +x transcribe

# Or run with python
python transcribe --help
```

#### "Out of memory"
```bash
# Use smaller model
python transcribe transcribe file.mp3 --model tiny

# Force chunking
python transcribe transcribe file.mp3 --force-chunking
```

## 📊 Performance Expectations

### Processing Speed (typical CPU)
- **tiny model**: 3-5x realtime
- **base model**: 1-2x realtime (recommended)
- **large model**: 0.5-1x realtime

### Accuracy Expectations
- **Clear speech**: 90-95%
- **Noisy audio**: 75-85%
- **Multiple speakers**: 80-90%

### Memory Usage
- **Standard processing**: ~1-2GB
- **Chunked processing**: <1GB regardless of file size

## 🎯 Next Steps

### Learn More
- [Full User Guide](USER_GUIDE.md) - Complete feature documentation
- [Configuration Guide](CONFIGURATION.md) - Customize settings
- [Installation Guide](INSTALLATION.md) - Detailed setup instructions

### Try Advanced Features
```bash
# Include timestamps
python transcribe transcribe meeting.mp4 --timestamps

# Specify language for better accuracy
python transcribe transcribe spanish.mp3 --language es

# Batch process with custom settings
python transcribe batch recordings/ --model large --format json
```

### Configuration
```bash
# View current settings
python transcribe config --show-config

# Create custom config file at ~/.transcription/config.yaml
```

## 💡 Pro Tips

1. **Specify language** when known for better accuracy:
   ```bash
   python transcribe transcribe file.mp3 --language en
   ```

2. **Use appropriate model** for your needs:
   - `tiny`: Testing, real-time needs
   - `base`: General use (recommended)
   - `large`: Maximum accuracy

3. **For large files**, let automatic chunking handle it:
   ```bash
   python transcribe transcribe huge_file.mp4  # Automatic chunking
   ```

4. **Batch processing** for multiple files:
   ```bash
   python transcribe batch folder/ --recursive
   ```

5. **JSON output** for structured data needs:
   ```bash
   python transcribe transcribe file.mp3 --format json --timestamps
   ```

## 🆘 Getting Help

### Built-in Help
```bash
python transcribe --help              # General help
python transcribe transcribe --help   # Transcribe command help
python transcribe batch --help        # Batch command help
```

### Check Your Setup
```bash
python transcribe version             # Version info
python transcribe config --show-config  # Current settings
```

### Documentation
- [User Guide](USER_GUIDE.md) - Complete usage guide
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Configuration](CONFIGURATION.md) - Advanced settings

---

**You're ready to start transcribing!** 🎉

Try transcribing your first file and explore the features. The tool is designed to be intuitive and handle most scenarios automatically.