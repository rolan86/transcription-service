# 📦 Installation Guide

Complete step-by-step installation guide for the Professional Transcription Service.

## System Requirements

### Minimum Requirements
- **Python**: 3.11 or higher
- **RAM**: 4GB (8GB recommended for large models)
- **Storage**: 5GB free space (for models and temporary files)
- **OS**: macOS, Linux, or Windows

### Recommended Requirements
- **Python**: 3.11+
- **RAM**: 8GB+ (16GB for large model)
- **Storage**: 10GB+ free space
- **CPU**: Multi-core processor
- **GPU**: CUDA-compatible GPU (optional, for faster processing)

## Step-by-Step Installation

### Step 1: Install System Dependencies

#### macOS
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install FFmpeg
brew install ffmpeg

# Install Python 3.11 (if needed)
brew install python@3.11
```

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install FFmpeg
sudo apt install ffmpeg

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install pip
sudo apt install python3-pip
```

#### CentOS/RHEL/Fedora
```bash
# Enable EPEL repository (CentOS/RHEL)
sudo yum install epel-release

# Install FFmpeg
sudo yum install ffmpeg

# Install Python 3.11
sudo yum install python3.11 python3.11-pip
```

#### Windows
```bash
# Install Chocolatey (if not already installed)
# Run as Administrator in PowerShell:
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install FFmpeg
choco install ffmpeg

# Install Python 3.11
choco install python311
```

#### Verify FFmpeg Installation
```bash
ffmpeg -version
```
You should see FFmpeg version information.

### Step 2: Download the Project

#### Option A: Download ZIP
1. Download the project ZIP file
2. Extract to your desired location
3. Navigate to the extracted directory

#### Option B: Git Clone (if available)
```bash
git clone https://github.com/yourusername/transcription-service.git
cd transcription-service
```

### Step 3: Set Up Python Environment

#### Create Virtual Environment
```bash
# Navigate to project directory
cd transcription-service

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### Verify Virtual Environment
```bash
# Check Python version
python --version
# Should show: Python 3.11.x

# Check pip
pip --version
```

### Step 4: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

This will install all required packages including:
- `openai-whisper` - Core transcription engine
- `click` - CLI framework
- `rich` - Beautiful terminal output
- `pyyaml` - Configuration management
- `tqdm` - Progress bars
- And other dependencies...

### Step 5: Verify Installation

#### Test Basic Functionality
```bash
# Check if the CLI works
python transcribe --help
```

You should see the welcome screen and command options.

#### Test Configuration
```bash
# Show current configuration
python transcribe config --show-config
```

#### Test with Sample File
```bash
# Create a simple test (optional)
echo "This is a test" | espeak -w test_audio.wav  # Linux with espeak
# Or download a sample audio file

# Test transcription
python transcribe transcribe test_audio.wav
```

## Installation Verification Checklist

- [ ] Python 3.11+ installed and accessible
- [ ] FFmpeg installed and in PATH
- [ ] Virtual environment created and activated
- [ ] All dependencies installed without errors
- [ ] CLI help command works
- [ ] Configuration display works
- [ ] Sample transcription works

## Platform-Specific Notes

### macOS
- **Apple Silicon (M1/M2)**: All dependencies are compatible
- **Intel Macs**: Full compatibility
- **Permissions**: May need to allow terminal access to microphone/files

### Linux
- **GPU Support**: Install CUDA if you have an NVIDIA GPU for faster processing
- **Audio Libraries**: May need additional audio libraries for some formats
- **Permissions**: Ensure user has access to audio/video files

### Windows
- **Path Issues**: Make sure Python and FFmpeg are in system PATH
- **Permissions**: Run terminal as Administrator if needed
- **WSL**: Can also install in Windows Subsystem for Linux

## GPU Support (Optional)

### NVIDIA GPU (CUDA)
If you have an NVIDIA GPU, you can enable GPU acceleration:

```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Apple Silicon (MPS)
For Apple Silicon Macs, Metal Performance Shaders (MPS) support is automatic with PyTorch 2.0+.

## Alternative Installation Methods

### Using pip (Future)
```bash
# Once published to PyPI
pip install transcription-service
```

### Using conda (Future)
```bash
# Once available on conda-forge
conda install -c conda-forge transcription-service
```

### Docker (Future)
```bash
# Pull and run Docker image
docker run -it transcription-service transcribe --help
```

## Post-Installation Configuration

### Create User Configuration
```bash
# Create config directory
mkdir -p ~/.transcription

# Create basic config file
cat > ~/.transcription/config.yaml << EOF
transcription:
  default_model: "base"
  default_language: null
  
output:
  default_format: "txt"
  include_metadata: true
  
logging:
  level: "INFO"
EOF
```

### Set Environment Variables (Optional)
```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export TRANSCRIPTION_MODEL="base"
export TRANSCRIPTION_OUTPUT_FORMAT="txt"
```

## System Integration (Optional)

### Make Command Globally Available
```bash
# Create symlink (Linux/macOS)
sudo ln -s /path/to/transcription-service/transcribe /usr/local/bin/transcribe

# Or add to PATH
echo 'export PATH="/path/to/transcription-service:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Desktop Integration (Linux)
```bash
# Create desktop entry
cat > ~/.local/share/applications/transcription-service.desktop << EOF
[Desktop Entry]
Name=Transcription Service
Comment=Audio/Video Transcription Tool
Exec=/path/to/transcription-service/transcribe
Icon=audio-x-generic
Terminal=true
Type=Application
Categories=AudioVideo;Audio;
EOF
```

## Troubleshooting Installation

### Common Issues

#### Python Version Issues
```bash
# If python3.11 not found
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Or use specific path
/usr/bin/python3.11 -m venv venv
```

#### FFmpeg Issues
```bash
# Test FFmpeg directly
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 test.mp4

# Check FFmpeg libraries
ffmpeg -formats | grep -E "(mp3|wav|mp4)"
```

#### Permission Issues
```bash
# Fix permissions (Linux/macOS)
chmod +x transcribe

# Or run with python explicitly
python transcribe --help
```

#### Dependency Conflicts
```bash
# Clean install
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install --no-cache-dir -r requirements.txt
```

### Getting Help

If you encounter issues:

1. **Check system requirements** - Ensure all prerequisites are met
2. **Verify installation steps** - Go through each step carefully
3. **Check error messages** - Look for specific error information
4. **Consult troubleshooting guide** - See docs/TROUBLESHOOTING.md
5. **Search existing issues** - Check GitHub issues for similar problems
6. **Create new issue** - Report new problems with system details

## Next Steps

After successful installation:

1. **Read the User Guide** - See docs/USER_GUIDE.md
2. **Try examples** - Start with simple transcription tasks
3. **Configure settings** - Customize for your workflow
4. **Explore advanced features** - Learn about batch processing and chunking

Congratulations! You now have the Professional Transcription Service installed and ready to use.