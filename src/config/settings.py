"""
Configuration management system for the transcription service.
Supports hierarchical configuration loading from multiple sources.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table

console = Console()

class Settings:
    """Configuration management with hierarchical loading."""
    
    DEFAULT_CONFIG = {
        'transcription': {
            'default_model': 'base',
            'default_language': None,
            'chunk_duration': 30,
            'enable_chunking_threshold': 300,  # 5 minutes
            'max_memory_mb': 1000,
            'parallel_chunks': False
        },
        'output': {
            'default_format': 'txt',
            'include_metadata': True,
            'timestamp_format': 'seconds',
            'auto_output_naming': True
        },
        'processing': {
            'temp_dir': None,  # Use system temp if None
            'cleanup_temp_files': True,
            'progress_reporting': True,
            'verbose_progress': False
        },
        'logging': {
            'level': 'INFO',
            'file': None,  # No file logging by default
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'whisper': {
            'cache_dir': None,  # Use Whisper's default if None
            'download_root': None,  # Use Whisper's default if None
            'download_timeout': 300,  # 5 minutes
            'no_progress': False
        },
        'enhancement': {
            'enable_speaker_detection': False,
            'expected_speakers': None,  # Auto-detect if None
            'include_speaker_labels': True,
            'include_speaker_confidence': False,
            'use_huggingface_token': False,
            'enable_audio_preprocessing': False,
            'noise_reduction': False,
            'volume_normalization': False,
            'high_pass_filter': False,
            'low_pass_filter': False,
            'enhance_speech': False,
            'target_sample_rate': None,
            'analyze_audio_quality': False,
            'enable_performance_optimizations': False,
            'enable_caching': True,
            'cache_directory': None,
            'memory_optimization': False,
            'parallel_workers': None,
            'show_performance_metrics': False,
            'enhanced_metadata': False,
            'enhanced_metadata_audio_analysis': True,
            'enhanced_metadata_content_analysis': True
        },
        'ai': {
            'provider': 'ollama',  # 'zai', 'claude', 'ollama', or 'llama'
            'zai': {
                'api_key': None,  # Set via env: ZAI_API_KEY
                'base_url': 'https://api.z.ai/v1',
            },
            'claude': {
                'api_key': None,  # Set via env: ANTHROPIC_API_KEY
                'model': 'claude-sonnet-4-20250514',
            },
            'ollama': {
                'model': 'llama3',  # Default Ollama model
                'base_url': 'http://localhost:11434',
            },
            'llama': {
                'model_path': None,  # Path to .gguf model file
                'n_ctx': 4096,
            },
            'semantic_search_enabled': True,
            'embedding_model': 'all-MiniLM-L6-v2',
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings with hierarchical loading.
        
        Args:
            config_file: Optional path to specific config file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_file_path = None
        
        # Load configuration in order of priority (lowest to highest)
        self._load_system_config()
        self._load_user_config()
        
        if config_file:
            self._load_config_file(config_file)
        
        self._load_environment_variables()
    
    def _load_system_config(self):
        """Load system-wide configuration."""
        system_config_path = Path('/etc/transcription-service/config.yaml')
        if system_config_path.exists():
            self._load_config_file(str(system_config_path))
    
    def _load_user_config(self):
        """Load user-specific configuration."""
        user_config_dir = Path.home() / '.transcription'
        user_config_path = user_config_dir / 'config.yaml'
        
        if user_config_path.exists():
            self._load_config_file(str(user_config_path))
            self.config_file_path = str(user_config_path)
        else:
            # Create default user config directory
            user_config_dir.mkdir(exist_ok=True)
            self.config_file_path = str(user_config_path)
    
    def _load_config_file(self, config_path: str):
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f) or {}
            
            # Deep merge configuration
            self._deep_merge(self.config, file_config)
            self.config_file_path = config_path
            
        except Exception as e:
            console.print(f"⚠️  Warning: Could not load config file {config_path}: {e}")
    
    def _load_environment_variables(self):
        """Load configuration from environment variables."""
        env_mapping = {
            # Core transcription settings
            'TRANSCRIPTION_MODEL': ('transcription', 'default_model'),
            'TRANSCRIPTION_LANGUAGE': ('transcription', 'default_language'),
            'TRANSCRIPTION_CHUNK_DURATION': ('transcription', 'chunk_duration'),
            'TRANSCRIPTION_FORCE_CHUNKING': ('transcription', 'force_chunking'),
            'TRANSCRIPTION_MAX_MEMORY_MB': ('transcription', 'max_memory_mb'),
            
            # Output settings
            'TRANSCRIPTION_OUTPUT_FORMAT': ('output', 'default_format'),
            'TRANSCRIPTION_INCLUDE_METADATA': ('output', 'include_metadata'),
            'TRANSCRIPTION_INCLUDE_TIMESTAMPS': ('output', 'include_timestamps'),
            'TRANSCRIPTION_TIMESTAMP_FORMAT': ('output', 'timestamp_format'),
            
            # Processing settings
            'TRANSCRIPTION_TEMP_DIR': ('processing', 'temp_dir'),
            'TRANSCRIPTION_CLEANUP_TEMP_FILES': ('processing', 'cleanup_temp_files'),
            'TRANSCRIPTION_PROGRESS_REPORTING': ('processing', 'progress_reporting'),
            'TRANSCRIPTION_VERBOSE_PROGRESS': ('processing', 'verbose_progress'),
            
            # Logging settings
            'TRANSCRIPTION_LOG_LEVEL': ('logging', 'level'),
            'TRANSCRIPTION_LOG_FILE': ('logging', 'file'),
            'TRANSCRIPTION_LOG_FORMAT': ('logging', 'format'),
            
            # Whisper-specific settings
            'WHISPER_CACHE_DIR': ('whisper', 'cache_dir'),
            'WHISPER_DOWNLOAD_ROOT': ('whisper', 'download_root'),
            'WHISPER_DOWNLOAD_TIMEOUT': ('whisper', 'download_timeout'),
            'WHISPER_NO_PROGRESS': ('whisper', 'no_progress'),

            # AI provider settings
            'AI_PROVIDER': ('ai', 'provider'),
        }

        # Handle nested AI provider settings
        ai_env_vars = {
            'ZAI_API_KEY': ('zai', 'api_key'),
            'ZAI_BASE_URL': ('zai', 'base_url'),
            'ANTHROPIC_API_KEY': ('claude', 'api_key'),
            'CLAUDE_MODEL': ('claude', 'model'),
            'OLLAMA_MODEL': ('ollama', 'model'),
            'OLLAMA_BASE_URL': ('ollama', 'base_url'),
            'LLAMA_MODEL_PATH': ('llama', 'model_path'),
        }

        for env_var, (provider, key) in ai_env_vars.items():
            value = os.getenv(env_var)
            if value is not None:
                if 'ai' not in self.config:
                    self.config['ai'] = {}
                if provider not in self.config['ai']:
                    self.config['ai'][provider] = {}
                self.config['ai'][provider][key] = value
        
        for env_var, (section, key) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion
                if key in ['chunk_duration', 'enable_chunking_threshold', 'max_memory_mb', 'download_timeout']:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif key in ['parallel_chunks', 'include_metadata', 'cleanup_temp_files', 
                           'progress_reporting', 'verbose_progress', 'force_chunking',
                           'include_timestamps', 'no_progress']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                
                self.config[section][key] = value
    
    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge two dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def update_from_args(self, args: Dict[str, Any]):
        """Update configuration from command-line arguments."""
        arg_mapping = {
            'model': ('transcription', 'default_model'),
            'language': ('transcription', 'default_language'),
            'chunk_duration': ('transcription', 'chunk_duration'),
            'force_chunking': ('transcription', 'force_chunking'),
            'output_format': ('output', 'default_format'),
            'timestamps': ('output', 'include_timestamps'),
            'verbose': ('processing', 'verbose_progress'),
            'quiet': ('processing', 'quiet_mode'),
            'enable_speaker_detection': ('enhancement', 'enable_speaker_detection'),
            'expected_speakers': ('enhancement', 'expected_speakers'),
            'include_speaker_labels': ('enhancement', 'include_speaker_labels'),
            'include_speaker_confidence': ('enhancement', 'include_speaker_confidence'),
            'use_huggingface_token': ('enhancement', 'use_huggingface_token'),
            'enable_audio_preprocessing': ('enhancement', 'enable_audio_preprocessing'),
            'noise_reduction': ('enhancement', 'noise_reduction'),
            'volume_normalization': ('enhancement', 'volume_normalization'),
            'high_pass_filter': ('enhancement', 'high_pass_filter'),
            'low_pass_filter': ('enhancement', 'low_pass_filter'),
            'enhance_speech': ('enhancement', 'enhance_speech'),
            'target_sample_rate': ('enhancement', 'target_sample_rate'),
            'analyze_audio_quality': ('enhancement', 'analyze_audio_quality'),
            'enable_performance_optimizations': ('enhancement', 'enable_performance_optimizations'),
            'enable_caching': ('enhancement', 'enable_caching'),
            'cache_directory': ('enhancement', 'cache_directory'),
            'memory_optimization': ('enhancement', 'memory_optimization'),
            'parallel_workers': ('enhancement', 'parallel_workers'),
            'show_performance_metrics': ('enhancement', 'show_performance_metrics'),
            'enhanced_metadata': ('enhancement', 'enhanced_metadata'),
            'enhanced_metadata_audio_analysis': ('enhancement', 'enhanced_metadata_audio_analysis'),
            'enhanced_metadata_content_analysis': ('enhancement', 'enhanced_metadata_content_analysis')
        }
        
        for arg_name, (section, key) in arg_mapping.items():
            if arg_name in args and args[arg_name] is not None:
                if section not in self.config:
                    self.config[section] = {}
                self.config[section][key] = args[arg_name]
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def save_user_config(self):
        """Save current configuration to user config file."""
        if not self.config_file_path:
            user_config_dir = Path.home() / '.transcription'
            user_config_dir.mkdir(exist_ok=True)
            self.config_file_path = str(user_config_dir / 'config.yaml')
        
        try:
            with open(self.config_file_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            console.print(f"✅ Configuration saved to {self.config_file_path}")
        except Exception as e:
            console.print(f"❌ Error saving configuration: {e}")
    
    def print_config(self):
        """Print current configuration in a nice table format."""
        table = Table(title="Current Configuration")
        table.add_column("Section", style="cyan", no_wrap=True)
        table.add_column("Setting", style="magenta")
        table.add_column("Value", style="green")
        
        for section_name, section_config in self.config.items():
            for key, value in section_config.items():
                table.add_row(section_name, key, str(value))
        
        console.print(table)
    
    @property
    def transcription_config(self) -> Dict[str, Any]:
        """Get transcription-specific configuration."""
        return self.config.get('transcription', {})
    
    @property
    def output_config(self) -> Dict[str, Any]:
        """Get output-specific configuration."""
        return self.config.get('output', {})
    
    @property
    def processing_config(self) -> Dict[str, Any]:
        """Get processing-specific configuration."""
        return self.config.get('processing', {})
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging-specific configuration."""
        return self.config.get('logging', {})
    
    @property
    def whisper_config(self) -> Dict[str, Any]:
        """Get Whisper-specific configuration."""
        return self.config.get('whisper', {})

    @property
    def ai_config(self) -> Dict[str, Any]:
        """Get AI-specific configuration."""
        return self.config.get('ai', {})