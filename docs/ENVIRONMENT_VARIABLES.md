# 🌍 Environment Variables Guide

Complete guide to configuring the Professional Transcription Service using environment variables, including OpenAI Whisper-specific settings.

## Overview

Environment variables provide a convenient way to configure the transcription service without modifying configuration files. They're especially useful for:
- **Docker deployments**
- **CI/CD pipelines**
- **Multi-environment setups**
- **Quick configuration changes**

## Setting Environment Variables

### Linux/macOS (Bash/Zsh)
```bash
# Set for current session
export TRANSCRIPTION_MODEL="large"

# Set permanently (add to ~/.bashrc, ~/.zshrc, etc.)
echo 'export TRANSCRIPTION_MODEL="large"' >> ~/.bashrc
source ~/.bashrc
```

### Windows (PowerShell)
```powershell
# Set for current session
$env:TRANSCRIPTION_MODEL="large"

# Set permanently
[Environment]::SetEnvironmentVariable("TRANSCRIPTION_MODEL", "large", "User")
```

### Using .env File
Create a `.env` file in your project directory:

```bash
# .env file
TRANSCRIPTION_MODEL=large
TRANSCRIPTION_LANGUAGE=en
WHISPER_CACHE_DIR=/path/to/whisper/cache
```

Then load it:
```bash
# Install python-dotenv (already included in requirements.txt)
pip install python-dotenv

# Load automatically (our service supports this)
python transcribe transcribe file.mp3
```

## Transcription Service Variables

### Core Transcription Settings
```bash
# Model size (tiny, base, small, medium, large)
export TRANSCRIPTION_MODEL="base"

# Default language (en, es, fr, etc. or null for auto-detect)
export TRANSCRIPTION_LANGUAGE="en"

# Chunk duration for large files (seconds)
export TRANSCRIPTION_CHUNK_DURATION=30

# Force chunking for all files
export TRANSCRIPTION_FORCE_CHUNKING=true

# Maximum memory usage (MB)
export TRANSCRIPTION_MAX_MEMORY_MB=1000
```

### Output Settings
```bash
# Default output format (txt, json)
export TRANSCRIPTION_OUTPUT_FORMAT="txt"

# Include metadata in output
export TRANSCRIPTION_INCLUDE_METADATA=true

# Include timestamps in output
export TRANSCRIPTION_INCLUDE_TIMESTAMPS=false

# Timestamp format (seconds, srt)
export TRANSCRIPTION_TIMESTAMP_FORMAT="seconds"
```

### Processing Settings
```bash
# Temporary directory for processing
export TRANSCRIPTION_TEMP_DIR="/tmp/transcription"

# Clean up temporary files after processing
export TRANSCRIPTION_CLEANUP_TEMP_FILES=true

# Enable progress reporting
export TRANSCRIPTION_PROGRESS_REPORTING=true

# Verbose progress output
export TRANSCRIPTION_VERBOSE_PROGRESS=false
```

### Logging Settings
```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export TRANSCRIPTION_LOG_LEVEL="INFO"

# Log file path (optional)
export TRANSCRIPTION_LOG_FILE="/var/log/transcription.log"

# Log format
export TRANSCRIPTION_LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## OpenAI Whisper Environment Variables

### Model and Cache Settings
```bash
# Whisper model cache directory
export WHISPER_CACHE_DIR="$HOME/.cache/whisper"

# Download root for models
export WHISPER_DOWNLOAD_ROOT="$HOME/.cache/whisper"

# Model download timeout (seconds)
export WHISPER_DOWNLOAD_TIMEOUT=300

# Disable progress bars during model download
export WHISPER_NO_PROGRESS=false
```

### GPU and Performance Settings
```bash
# Force CPU usage (disable GPU)
export CUDA_VISIBLE_DEVICES=""

# Enable CUDA device debugging
export CUDA_LAUNCH_BLOCKING=1

# PyTorch CUDA memory fraction
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"

# Number of threads for CPU processing
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

### Network and Proxy Settings
```bash
# HTTP proxy for model downloads
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"

# No proxy for certain domains
export NO_PROXY="localhost,127.0.0.1,.local"

# Disable SSL verification (not recommended for production)
export PYTHONHTTPSVERIFY=0
```

## Complete .env File Example

```bash
# ==================================================
# Professional Transcription Service Configuration
# ==================================================

# Core Transcription Settings
TRANSCRIPTION_MODEL=base
TRANSCRIPTION_LANGUAGE=en
TRANSCRIPTION_CHUNK_DURATION=30
TRANSCRIPTION_FORCE_CHUNKING=false
TRANSCRIPTION_MAX_MEMORY_MB=2000

# Output Configuration
TRANSCRIPTION_OUTPUT_FORMAT=txt
TRANSCRIPTION_INCLUDE_METADATA=true
TRANSCRIPTION_INCLUDE_TIMESTAMPS=false
TRANSCRIPTION_TIMESTAMP_FORMAT=seconds

# Processing Settings
TRANSCRIPTION_TEMP_DIR=/tmp/transcription
TRANSCRIPTION_CLEANUP_TEMP_FILES=true
TRANSCRIPTION_PROGRESS_REPORTING=true
TRANSCRIPTION_VERBOSE_PROGRESS=false

# Logging Configuration
TRANSCRIPTION_LOG_LEVEL=INFO
TRANSCRIPTION_LOG_FILE=/var/log/transcription/app.log
TRANSCRIPTION_LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ==================================================
# OpenAI Whisper Settings
# ==================================================

# Model Storage and Caching
WHISPER_CACHE_DIR=/opt/whisper/models
WHISPER_DOWNLOAD_ROOT=/opt/whisper/models
WHISPER_DOWNLOAD_TIMEOUT=600
WHISPER_NO_PROGRESS=false

# Performance Settings
OMP_NUM_THREADS=8
MKL_NUM_THREADS=8

# GPU Settings (uncomment if you want to force CPU)
# CUDA_VISIBLE_DEVICES=""

# Memory Management
PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:256"

# Network Settings (uncomment if behind proxy)
# HTTP_PROXY=http://proxy.company.com:8080
# HTTPS_PROXY=http://proxy.company.com:8080
# NO_PROXY=localhost,127.0.0.1,.local

# ==================================================
# System Settings
# ==================================================

# Python Settings
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# FFmpeg Settings
FFMPEG_BINARY=/usr/local/bin/ffmpeg
```

## Environment-Specific Configurations

### Development Environment
```bash
# .env.development
TRANSCRIPTION_MODEL=tiny
TRANSCRIPTION_LOG_LEVEL=DEBUG
TRANSCRIPTION_VERBOSE_PROGRESS=true
WHISPER_CACHE_DIR=./cache/whisper
TRANSCRIPTION_TEMP_DIR=./tmp
```

### Production Environment
```bash
# .env.production
TRANSCRIPTION_MODEL=large
TRANSCRIPTION_LOG_LEVEL=INFO
TRANSCRIPTION_LOG_FILE=/var/log/transcription/production.log
WHISPER_CACHE_DIR=/opt/whisper/cache
TRANSCRIPTION_TEMP_DIR=/opt/transcription/tmp
TRANSCRIPTION_MAX_MEMORY_MB=8000
```

### CI/CD Environment
```bash
# .env.ci
TRANSCRIPTION_MODEL=tiny
TRANSCRIPTION_LOG_LEVEL=WARNING
TRANSCRIPTION_CLEANUP_TEMP_FILES=true
TRANSCRIPTION_PROGRESS_REPORTING=false
WHISPER_NO_PROGRESS=true
```

## Loading Environment Variables

### Automatic Loading
Our service automatically loads environment variables in this order:

1. **System environment variables**
2. **`.env` file in project directory**
3. **Command-line arguments** (highest priority)

### Manual Loading
```bash
# Load from specific .env file
python transcribe transcribe file.mp3 --config .env.production

# Load with python-dotenv
python -c "from dotenv import load_dotenv; load_dotenv('.env.custom')"
```

### Verify Current Settings
```bash
# Show all current configuration (including env vars)
python transcribe config --show-config

# Check specific environment variables
env | grep TRANSCRIPTION
env | grep WHISPER
```

## Docker Integration

### Dockerfile Example
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Set environment variables
ENV TRANSCRIPTION_MODEL=base
ENV WHISPER_CACHE_DIR=/app/cache/whisper
ENV TRANSCRIPTION_TEMP_DIR=/app/tmp

# Copy application
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Create directories
RUN mkdir -p /app/cache/whisper /app/tmp

# Set entrypoint
ENTRYPOINT ["python", "transcribe"]
```

### Docker Compose Example
```yaml
version: '3.8'
services:
  transcription:
    build: .
    environment:
      - TRANSCRIPTION_MODEL=large
      - TRANSCRIPTION_LOG_LEVEL=INFO
      - WHISPER_CACHE_DIR=/app/cache
      - TRANSCRIPTION_TEMP_DIR=/app/tmp
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache
      - ./tmp:/app/tmp
    env_file:
      - .env.production
```

## Kubernetes Configuration

### ConfigMap Example
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: transcription-config
data:
  TRANSCRIPTION_MODEL: "large"
  TRANSCRIPTION_LOG_LEVEL: "INFO"
  WHISPER_CACHE_DIR: "/app/cache/whisper"
  TRANSCRIPTION_TEMP_DIR: "/app/tmp"
```

### Secret Example
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: transcription-secrets
type: Opaque
stringData:
  HTTP_PROXY: "http://proxy.company.com:8080"
  TRANSCRIPTION_LOG_FILE: "/var/log/transcription.log"
```

## Troubleshooting Environment Variables

### Check if Variables are Set
```bash
# List all transcription-related variables
env | grep -E "(TRANSCRIPTION|WHISPER)" | sort

# Check specific variable
echo $TRANSCRIPTION_MODEL

# Verify in Python
python -c "import os; print(f'Model: {os.getenv(\"TRANSCRIPTION_MODEL\", \"not set\")}')"
```

### Variable Priority Issues
```bash
# Show configuration with sources
python transcribe config --show-config --verbose

# Test with specific environment
TRANSCRIPTION_MODEL=tiny python transcribe transcribe file.mp3 --verbose
```

### Common Issues

#### Variables Not Loading
```bash
# Check .env file format (no spaces around =)
cat .env | grep -v "^#" | grep "="

# Verify python-dotenv is installed
pip show python-dotenv

# Test manual loading
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.environ.get('TRANSCRIPTION_MODEL'))"
```

#### Wrong Variable Types
```bash
# Boolean values should be: true/false, 1/0, yes/no
export TRANSCRIPTION_FORCE_CHUNKING=true  # ✅ Correct
export TRANSCRIPTION_FORCE_CHUNKING=True  # ❌ Wrong

# Integer values should be plain numbers
export TRANSCRIPTION_CHUNK_DURATION=30    # ✅ Correct
export TRANSCRIPTION_CHUNK_DURATION="30"  # ✅ Also works
```

## Security Considerations

### Sensitive Information
```bash
# Don't put sensitive data in .env files that might be committed
# Use system environment variables or secret management instead

# Good for local development
TRANSCRIPTION_MODEL=base

# Avoid in .env files (use system env or secrets)
# HTTP_PROXY=http://user:password@proxy.com:8080
```

### File Permissions
```bash
# Secure .env files
chmod 600 .env
chown $(whoami):$(whoami) .env

# Don't commit .env files
echo ".env*" >> .gitignore
```

## Best Practices

1. **Use specific .env files** for different environments
2. **Document all variables** in your .env.example file
3. **Validate required variables** on startup
4. **Use reasonable defaults** for optional variables
5. **Keep sensitive data** in system environment or secret management
6. **Test configuration** changes before deployment

## Integration Examples

### Shell Script Integration
```bash
#!/bin/bash
# transcribe_batch.sh

# Load environment
source .env.production

# Process files with environment settings
for file in *.mp3; do
    python transcribe transcribe "$file" \
        --model "$TRANSCRIPTION_MODEL" \
        --format "$TRANSCRIPTION_OUTPUT_FORMAT"
done
```

### Python Integration
```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.production')

# Use in your code
model = os.getenv('TRANSCRIPTION_MODEL', 'base')
print(f"Using model: {model}")
```

This comprehensive environment variable support makes the transcription service highly configurable and suitable for various deployment scenarios!