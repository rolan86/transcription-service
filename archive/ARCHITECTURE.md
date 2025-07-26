# System Architecture

## Overview
The transcription service follows a modular architecture with clear separation of concerns, making it maintainable and extensible.

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Core Engine    │────│   Output Layer  │
│                 │    │                 │    │                 │
│ - Argument      │    │ - File Handler  │    │ - Text Writer   │
│   Parsing       │    │ - Audio         │    │ - JSON Writer   │
│ - Validation    │    │   Processor     │    │ - SRT Writer    │
│ - Progress      │    │ - Transcription │    │ - Formatter     │
│   Display       │    │   Engine        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Shared Utils   │
                    │                 │
                    │ - Config Mgmt   │
                    │ - Logging       │
                    │ - Error Handler │
                    │ - File Utils    │
                    └─────────────────┘
```

## Component Details

### 1. CLI Interface Layer (`cli/`)
**Responsibility**: User interaction and command processing

**Components**:
- `main.py`: Entry point and argument parsing
- `commands.py`: Command handlers for different operations
- `validators.py`: Input validation logic
- `progress.py`: Progress display utilities

**Technologies**:
- `click` for CLI framework
- `tqdm` for progress bars
- `rich` for enhanced terminal output (post-MVP)

### 2. Core Engine (`core/`)
**Responsibility**: Main business logic and processing

**Components**:
- `file_handler.py`: File I/O operations and validation
- `audio_processor.py`: Audio extraction and preprocessing
- `transcription_engine.py`: Speech-to-text processing
- `batch_processor.py`: Multi-file processing logic

**Technologies**:
- `pydub` for audio manipulation
- `ffmpeg-python` for video processing (POC: MP4, MVP: MOV/AVI)
- `whisper` for transcription (robust, local processing)
- `concurrent.futures` for parallel processing

### 3. Output Layer (`output/`)
**Responsibility**: Result formatting and file writing

**Components**:
- `base_writer.py`: Abstract base class for writers
- `text_writer.py`: Plain text output
- `json_writer.py`: Structured JSON output
- `srt_writer.py`: Subtitle format output
- `formatter.py`: Text formatting utilities

### 4. Shared Utils (`utils/`)
**Responsibility**: Common functionality across modules

**Components**:
- `config.py`: Configuration management
- `logger.py`: Logging setup and utilities
- `exceptions.py`: Custom exception classes
- `file_utils.py`: File system utilities
- `constants.py`: Application constants

## Data Flow

### Single File Processing
```
Input File (MP3/WAV/MP4) → Validation → Format Detection → Audio Extraction 
     ↓
Audio Preprocessing → Transcription → Post-processing → Output

POC Flow:
MP3/WAV → Direct Processing → Whisper → Console Output
MP4 → FFmpeg Extract → Audio Processing → Whisper → Console Output
```

### Batch Processing
```
Input Directory → File Discovery → Queue Creation → Parallel Processing
                                      ↓
                              Individual File Processing → Aggregated Results
```

## Directory Structure
```
transcription-service/
├── src/
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── commands.py
│   │   └── validators.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── file_handler.py
│   │   ├── audio_processor.py
│   │   ├── transcription_engine.py
│   │   └── batch_processor.py
│   ├── output/
│   │   ├── __init__.py
│   │   ├── base_writer.py
│   │   ├── text_writer.py
│   │   ├── json_writer.py
│   │   └── srt_writer.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       ├── logger.py
│       ├── exceptions.py
│       └── file_utils.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── config/
│   └── default.yaml
├── requirements.txt
├── setup.py
└── README.md
```

## Design Patterns

### 1. Strategy Pattern
Used in transcription engine to support multiple speech recognition backends:
```python
class TranscriptionStrategy:
    def transcribe(self, audio_data): pass

class WhisperStrategy(TranscriptionStrategy): pass
class GoogleStrategy(TranscriptionStrategy): pass
```

### 2. Factory Pattern
Used for creating appropriate output writers:
```python
class WriterFactory:
    @staticmethod
    def create_writer(format_type):
        if format_type == 'txt': return TextWriter()
        elif format_type == 'json': return JsonWriter()
        # etc.
```

### 3. Observer Pattern (Post-MVP)
Used for progress reporting across different processing stages:
```python
class ProgressObserver:
    def update(self, progress, message): pass
```

## Configuration Management

### Configuration Hierarchy
1. Command-line arguments (highest priority)
2. Environment variables
3. User config file (`~/.transcription/config.yaml`)
4. Default config file
5. Built-in defaults (lowest priority)

### Configuration Schema
```yaml
transcription:
  engine: "whisper"  # whisper, google, azure
  model: "base"      # tiny, base, small, medium, large
  language: "auto"   # auto-detect or specific language code
  
audio:
  sample_rate: 16000
  channels: 1
  format: "wav"
  
output:
  format: "txt"      # txt, json, srt, vtt
  include_timestamps: true
  include_confidence: false
  
processing:
  batch_size: 5
  max_workers: 4
  chunk_duration: 30  # seconds
```

## Error Handling Strategy

### Error Categories
1. **Input Errors**: Invalid files, unsupported formats
2. **Processing Errors**: Transcription failures, memory issues
3. **Output Errors**: Write permissions, disk space
4. **System Errors**: Missing dependencies, network issues

### Error Response
- Graceful degradation where possible
- Clear, actionable error messages
- Proper cleanup of temporary files
- Logging for debugging purposes

## Performance Considerations

### Memory Management
- Stream processing for large files
- Chunk-based audio processing
- Cleanup of temporary files

### Processing Optimization
- Parallel processing for batch operations
- Audio preprocessing optimization
- Model caching for repeated transcriptions

### Scalability
- Configurable worker threads
- Memory usage monitoring
- Progress reporting for long operations

## Security Considerations

### Input Validation
- File type verification
- Size limits enforcement
- Path traversal prevention

### Data Privacy
- Local processing by default
- Secure temporary file handling
- No data transmission to external services (unless explicitly configured)

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock external dependencies
- Edge case validation

### Integration Tests
- End-to-end workflow testing
- Real file processing
- Error scenario testing

### Performance Tests
- Large file processing
- Memory usage validation
- Concurrent processing limits