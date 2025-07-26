# 🔧 Troubleshooting Guide

Common issues and solutions for the Professional Transcription Service.

## Quick Diagnosis

### Run System Check
```bash
# Check if basic components work
python transcribe --help
python transcribe version
python transcribe config --show-config

# Test FFmpeg
ffmpeg -version

# Test Python environment
python --version
pip list | grep -E "(whisper|torch|click)"
```

## Installation Issues

### Python Version Problems

#### Issue: "Python 3.11 not found"
**Symptoms:**
```
bash: python3.11: command not found
```

**Solutions:**
```bash
# Check available Python versions
ls /usr/bin/python*

# Use available version (must be 3.11+)
python3 --version

# If 3.11+ is default, create venv with:
python3 -m venv venv

# Install Python 3.11 if needed:
# Ubuntu/Debian:
sudo apt install python3.11 python3.11-venv

# macOS:
brew install python@3.11

# Windows:
choco install python311
```

#### Issue: Virtual Environment Creation Fails
**Symptoms:**
```
Error: Unable to create virtual environment
```

**Solutions:**
```bash
# Ensure venv module is available
python3.11 -m pip install --user virtualenv

# Try alternative approach
python3.11 -m virtualenv venv

# Or use conda if available
conda create -n transcription python=3.11
conda activate transcription
```

### FFmpeg Issues

#### Issue: "FFmpeg not found" or "FFmpeg not in PATH"
**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**Solutions:**
```bash
# Install FFmpeg
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL:
sudo yum install epel-release
sudo yum install ffmpeg

# Windows:
choco install ffmpeg

# Verify installation
ffmpeg -version
which ffmpeg  # Should show path
```

#### Issue: FFmpeg Permissions
**Symptoms:**
```
Permission denied: ffmpeg
```

**Solutions:**
```bash
# Check FFmpeg permissions
ls -la $(which ffmpeg)

# Fix permissions (Linux/macOS)
sudo chmod +x $(which ffmpeg)

# Add to PATH if needed
export PATH="/usr/local/bin:$PATH"
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
```

### Dependency Installation Issues

#### Issue: Pip Installation Fails
**Symptoms:**
```
ERROR: Could not install packages due to an EnvironmentError
```

**Solutions:**
```bash
# Update pip
pip install --upgrade pip

# Clear pip cache
pip cache purge

# Install with verbose output to see specific errors
pip install -r requirements.txt -v

# Try installing without cache
pip install --no-cache-dir -r requirements.txt

# If permissions issue (Linux/macOS)
pip install --user -r requirements.txt
```

#### Issue: PyTorch Installation Problems
**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement torch
```

**Solutions:**
```bash
# Install PyTorch manually first
# CPU version:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# CUDA version (if you have NVIDIA GPU):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Then install other requirements
pip install -r requirements.txt
```

## Runtime Issues

### Model Loading Problems

#### Issue: "Model download fails"
**Symptoms:**
```
URLError: <urlopen error [Errno -2] Name or service not known>
```

**Solutions:**
```bash
# Check internet connection
ping google.com

# Try downloading model manually
python -c "import whisper; whisper.load_model('base')"

# Use different model size
python transcribe transcribe file.mp3 --model tiny

# Set proxy if needed
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

#### Issue: "CUDA out of memory"
**Symptoms:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**
```bash
# Use smaller model
python transcribe transcribe file.mp3 --model tiny

# Force CPU usage
CUDA_VISIBLE_DEVICES="" python transcribe transcribe file.mp3

# Enable chunking
python transcribe transcribe file.mp3 --force-chunking

# Reduce chunk size
python transcribe transcribe file.mp3 --chunk-duration 15
```

### File Processing Issues

#### Issue: "Unsupported file format"
**Symptoms:**
```
Unsupported format: .xyz. Supported: {'.mp3', '.wav', '.mp4'}
```

**Solutions:**
```bash
# Check file format
file your_file.xyz

# Convert to supported format using FFmpeg
ffmpeg -i input.xyz output.mp3

# List supported formats
python transcribe transcribe --help | grep -A 5 "Supported formats"
```

#### Issue: "File not found"
**Symptoms:**
```
File not found: /path/to/file.mp3
```

**Solutions:**
```bash
# Check file exists
ls -la /path/to/file.mp3

# Use absolute path
python transcribe transcribe "$(pwd)/file.mp3"

# Check file permissions
chmod 644 file.mp3

# Verify file is not corrupted
ffprobe file.mp3
```

#### Issue: "Empty or corrupted file"
**Symptoms:**
```
File is empty
Error processing audio file
```

**Solutions:**
```bash
# Check file size
ls -lh file.mp3

# Test file with FFmpeg
ffmpeg -i file.mp3 -t 10 test_output.wav

# Try re-downloading or re-creating the file
# Check if file is actually audio/video
file file.mp3
```

### Memory and Performance Issues

#### Issue: "System out of memory"
**Symptoms:**
```
MemoryError: Unable to allocate array
System freezes during processing
```

**Solutions:**
```bash
# Use tiny model
python transcribe transcribe file.mp3 --model tiny

# Enable chunking for all files
python transcribe transcribe file.mp3 --force-chunking --chunk-duration 15

# Monitor memory usage
python transcribe transcribe file.mp3 --verbose

# Close other applications
# Check available memory
free -h  # Linux
vm_stat  # macOS
```

#### Issue: "Very slow processing"
**Symptoms:**
- Processing much slower than expected
- No progress for long periods

**Solutions:**
```bash
# Use smaller model
python transcribe transcribe file.mp3 --model tiny

# Check if GPU is being used
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Enable verbose output to see progress
python transcribe transcribe file.mp3 --verbose

# Check system resources
top    # Linux/macOS
htop   # If available
```

### Output Issues

#### Issue: "Permission denied writing output"
**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: 'output.txt'
```

**Solutions:**
```bash
# Check directory permissions
ls -la $(dirname output.txt)

# Use different output directory
python transcribe transcribe file.mp3 --output ~/transcripts/output.txt

# Create output directory first
mkdir -p transcripts
python transcribe transcribe file.mp3 --output transcripts/output.txt

# Fix permissions
chmod 755 output_directory
```

#### Issue: "Invalid JSON output"
**Symptoms:**
```
json.decoder.JSONDecodeError: Expecting value
```

**Solutions:**
```bash
# Check if output file exists and has content
ls -la output.json
head output.json

# Try regenerating
rm output.json
python transcribe transcribe file.mp3 --format json --output output.json

# Use text format instead
python transcribe transcribe file.mp3 --format txt
```

## Configuration Issues

### Issue: "Configuration not loading"
**Symptoms:**
- Settings from config file not being applied
- Default values always used

**Solutions:**
```bash
# Check config file location
python transcribe config --config-path

# Verify config file syntax
python -c "import yaml; print(yaml.safe_load(open('~/.transcription/config.yaml')))"

# Show current configuration
python transcribe config --show-config

# Use specific config file
python transcribe transcribe file.mp3 --config /path/to/config.yaml

# Recreate config directory
mkdir -p ~/.transcription
```

### Issue: "Environment variables not working"
**Symptoms:**
- Environment variables ignored
- Settings not applied

**Solutions:**
```bash
# Check environment variables are set
env | grep TRANSCRIPTION

# Export variables properly
export TRANSCRIPTION_MODEL="base"
export TRANSCRIPTION_LANGUAGE="en"

# Add to shell profile for persistence
echo 'export TRANSCRIPTION_MODEL="base"' >> ~/.bashrc
source ~/.bashrc

# Test with explicit values
TRANSCRIPTION_MODEL=tiny python transcribe transcribe file.mp3
```

## Advanced Troubleshooting

### Debug Mode
```bash
# Enable verbose logging
python transcribe transcribe file.mp3 --verbose

# Python debug mode
PYTHONPATH=src python -u transcribe transcribe file.mp3 --verbose

# Check individual components
python -c "from src.poc.file_handler import FileHandler; print(FileHandler.get_supported_formats())"
```

### System Information Collection
```bash
# Create debug report
cat > debug_info.txt << EOF
System: $(uname -a)
Python: $(python --version)
FFmpeg: $(ffmpeg -version | head -1)
GPU: $(python -c "import torch; print(torch.cuda.is_available())")
Memory: $(free -h | head -2)
Disk: $(df -h .)
EOF

# Package versions
pip list > installed_packages.txt
```

### Log File Analysis
```bash
# Enable file logging
mkdir -p ~/.transcription/logs
python transcribe transcribe file.mp3 --verbose 2>&1 | tee ~/.transcription/logs/debug.log

# Analyze logs
grep -i error ~/.transcription/logs/debug.log
grep -i warning ~/.transcription/logs/debug.log
```

## Common Error Messages

### "No module named 'whisper'"
**Solution:**
```bash
# Reinstall whisper
pip uninstall openai-whisper
pip install openai-whisper
```

### "CUDA driver version is insufficient"
**Solution:**
```bash
# Use CPU mode
CUDA_VISIBLE_DEVICES="" python transcribe transcribe file.mp3

# Or update CUDA drivers
# Check NVIDIA website for latest drivers
```

### "Connection timeout" during model download
**Solution:**
```bash
# Increase timeout
export WHISPER_DOWNLOAD_TIMEOUT=300

# Use mirror if available
# Download model manually and place in cache directory
```

### "Disk space insufficient"
**Solution:**
```bash
# Check disk space
df -h

# Clean up temporary files
rm -rf /tmp/tmp*
python -c "import tempfile; print(tempfile.gettempdir())"

# Use different temporary directory
export TMPDIR=/path/to/large/disk
```

## Performance Optimization

### For Large Files
```bash
# Optimal chunk size based on available memory
# 4GB RAM: --chunk-duration 15
# 8GB RAM: --chunk-duration 30 (default)
# 16GB+ RAM: --chunk-duration 60

python transcribe transcribe large_file.mp4 --chunk-duration 30
```

### For Batch Processing
```bash
# Process files sequentially to avoid memory issues
python transcribe batch directory/ --model base

# Monitor system resources during batch processing
```

### Model Selection Guidelines
- **tiny**: Testing, low-resource systems
- **base**: General use, good balance (recommended)
- **small**: Better accuracy, moderate resources
- **medium**: High accuracy, requires more resources
- **large**: Maximum accuracy, high-end systems only

## Getting Additional Help

### Verbose Output
Always include verbose output when reporting issues:
```bash
python transcribe transcribe problematic_file.mp3 --verbose
```

### System Information
Include system details:
```bash
# Operating system
uname -a

# Python version
python --version

# Installed packages
pip list | grep -E "(whisper|torch|click|pydub)"

# Hardware information
# Linux:
lscpu | head -10
free -h

# macOS:
system_profiler SPHardwareDataType
```

### Creating Bug Reports
When creating a bug report, include:

1. **Command used**: Exact command that failed
2. **Error message**: Complete error output
3. **System info**: OS, Python version, hardware
4. **File info**: File format, size, duration (if not sensitive)
5. **Configuration**: Output of `python transcribe config --show-config`
6. **Verbose output**: Output with `--verbose` flag

### Community Resources
- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and community support
- **Documentation**: Check all docs in `docs/` directory

Remember: Most issues are related to environment setup or file format problems. Following the installation guide carefully usually resolves most problems.