"""
Professional CLI interface for the transcription service.
Built with Click for intuitive command-line experience.
"""

import click
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from utils.logger import setup_logger
from core.transcription_service import TranscriptionService

console = Console()

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    🎙️ Professional Audio/Video Transcription Service
    
    Transform your audio and video files into accurate text transcripts
    with support for multiple formats and advanced processing options.
    """
    if ctx.invoked_subcommand is None:
        # Show welcome message when no subcommand is provided
        welcome_text = Text()
        welcome_text.append("🎙️ ", style="bold blue")
        welcome_text.append("Professional Transcription Service", style="bold")
        
        welcome_panel = Panel(
            Text.from_markup(
                "Transform audio and video files into text transcripts\n\n"
                "[bold blue]Supported formats:[/bold blue]\n"
                "• Audio: MP3, WAV, FLAC, M4A\n"
                "• Video: MP4, MOV, AVI\n\n"
                "[bold green]Quick start:[/bold green]\n"
                "  transcribe audio.mp3\n"
                "  transcribe video.mp4 --output transcript.txt\n\n"
                "[bold yellow]For help:[/bold yellow] transcribe --help"
            ),
            title=welcome_text,
            border_style="blue"
        )
        console.print(welcome_panel)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), 
              help='Output file path (default: auto-generated)')
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['txt', 'json', 'srt', 'vtt'], case_sensitive=False),
              default='txt', help='Output format: txt, json, srt, vtt (default: txt)')
@click.option('--model', '-m',
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
              default='base', help='Whisper model size (default: base)')
@click.option('--language', '-l',
              help='Language code (e.g., en, es, fr) or auto-detect if not specified')
@click.option('--timestamps/--no-timestamps', default=False,
              help='Include timestamps in output')
@click.option('--chunk-duration', type=int, default=30,
              help='Chunk duration for large files in seconds (default: 30)')
@click.option('--force-chunking', is_flag=True,
              help='Force chunked processing for all files')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True,
              help='Suppress progress output')
@click.option('--config', type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--speakers/--no-speakers', default=False,
              help='Enable speaker detection and diarization')
@click.option('--num-speakers', type=int,
              help='Expected number of speakers (optional hint)')
@click.option('--speaker-labels/--no-speaker-labels', default=True,
              help='Include speaker labels in output (default: enabled when --speakers used)')
@click.option('--speaker-confidence/--no-speaker-confidence', default=False,
              help='Include speaker confidence scores in output')
@click.option('--use-hf-token/--no-hf-token', default=False,
              help='Use HuggingFace token for better speaker detection models')
def transcribe(input_file, output, output_format, model, language, timestamps, 
               chunk_duration, force_chunking, verbose, quiet, config, 
               speakers, num_speakers, speaker_labels, speaker_confidence, use_hf_token):
    """
    Transcribe an audio or video file to text.
    
    INPUT_FILE: Path to the audio or video file to transcribe
    
    Examples:
    
      # Basic transcription
      transcribe audio.mp3
      
      # Specify output file and format
      transcribe video.mp4 --output transcript.txt --format txt
      
      # Use specific model and language
      transcribe recording.wav --model large --language en
      
      # Include timestamps
      transcribe meeting.mp4 --timestamps --format json
      
      # Process large file with custom chunk size
      transcribe long_video.mp4 --chunk-duration 60
    """
    try:
        # Initialize settings
        settings = Settings(config_file=config)
        
        # Set up logging
        log_level = 'DEBUG' if verbose else 'WARNING' if quiet else 'INFO'
        logger = setup_logger(level=log_level)
        
        # Override settings with command-line arguments
        settings.update_from_args({
            'model': model,
            'language': language,
            'timestamps': timestamps,
            'chunk_duration': chunk_duration,
            'force_chunking': force_chunking,
            'output_format': output_format,
            'verbose': verbose,
            'quiet': quiet,
            'enable_speaker_detection': speakers,
            'expected_speakers': num_speakers,
            'include_speaker_labels': speaker_labels if speakers else False,
            'include_speaker_confidence': speaker_confidence,
            'use_huggingface_token': use_hf_token
        })
        
        # Show processing info
        if not quiet:
            console.print(f"\n🎙️  [bold blue]Transcription Service[/bold blue]")
            console.print(f"📁 Input: {input_file}")
            console.print(f"📝 Format: {output_format.upper()}")
            console.print(f"🤖 Model: {model}")
            if language:
                console.print(f"🌍 Language: {language}")
            console.print()
        
        # Initialize transcription service
        service = TranscriptionService(settings, logger)
        
        # Process the file
        result = service.transcribe_file(
            input_file=input_file,
            output_file=output,
            output_format=output_format
        )
        
        if result['success']:
            if not quiet:
                console.print(f"✅ [bold green]Transcription completed successfully![/bold green]")
                console.print(f"📄 Output: {result['output_file']}")
                console.print(f"⏱️  Processing time: {result['processing_time']:.2f}s")
                console.print(f"📊 Confidence: {result['confidence']:.1%}")
        else:
            console.print(f"❌ [bold red]Transcription failed:[/bold red] {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n❌ [yellow]Transcription interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Unexpected error:[/bold red] {str(e)}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--output-dir', '-o', type=click.Path(file_okay=False, dir_okay=True),
              help='Output directory (default: same as input directory)')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['txt', 'json', 'srt', 'vtt'], case_sensitive=False),
              default='txt', help='Output format: txt, json, srt, vtt (default: txt)')
@click.option('--model', '-m',
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
              default='base', help='Whisper model size (default: base)')
@click.option('--language', '-l',
              help='Language code (e.g., en, es, fr) or auto-detect if not specified')
@click.option('--timestamps/--no-timestamps', default=False,
              help='Include timestamps in output')
@click.option('--recursive', '-r', is_flag=True,
              help='Process files recursively in subdirectories')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
@click.option('--config', type=click.Path(exists=True),
              help='Path to configuration file')
def batch(input_dir, output_dir, output_format, model, language, timestamps,
          recursive, verbose, config):
    """
    Batch transcribe multiple files in a directory.
    
    INPUT_DIR: Directory containing audio/video files to transcribe
    
    Examples:
    
      # Process all files in a directory
      transcribe batch recordings/
      
      # Process recursively with specific output directory
      transcribe batch media/ --output-dir transcripts/ --recursive
      
      # Batch process with specific settings
      transcribe batch meetings/ --format json --timestamps --model large
    """
    try:
        # Initialize settings
        settings = Settings(config_file=config)
        
        # Set up logging
        log_level = 'DEBUG' if verbose else 'INFO'
        logger = setup_logger(level=log_level)
        
        # Override settings with command-line arguments
        settings.update_from_args({
            'model': model,
            'language': language,
            'timestamps': timestamps,
            'output_format': output_format,
            'verbose': verbose,
            'recursive': recursive
        })
        
        console.print(f"\n📁 [bold blue]Batch Transcription[/bold blue]")
        console.print(f"📂 Input directory: {input_dir}")
        console.print(f"📝 Format: {output_format.upper()}")
        console.print(f"🤖 Model: {model}")
        console.print(f"🔄 Recursive: {'Yes' if recursive else 'No'}")
        console.print()
        
        # Initialize transcription service
        service = TranscriptionService(settings, logger)
        
        # Process batch
        result = service.batch_transcribe(
            input_dir=input_dir,
            output_dir=output_dir,
            output_format=output_format,
            recursive=recursive
        )
        
        if result['success']:
            console.print(f"✅ [bold green]Batch transcription completed![/bold green]")
            console.print(f"📊 Processed: {result['processed_files']}/{result['total_files']} files")
            console.print(f"⏱️  Total time: {result['total_time']:.2f}s")
        else:
            console.print(f"❌ [bold red]Batch transcription failed:[/bold red] {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n❌ [yellow]Batch transcription interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Unexpected error:[/bold red] {str(e)}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option('--show-config', is_flag=True,
              help='Show current configuration')
@click.option('--config-path', type=click.Path(),
              help='Show or set configuration file path')
def config_cmd(show_config, config_path):
    """
    Manage configuration settings.
    
    Examples:
    
      # Show current configuration
      transcribe config --show-config
      
      # Show configuration file path
      transcribe config --config-path
    """
    try:
        settings = Settings()
        
        if show_config:
            console.print("\n⚙️  [bold blue]Current Configuration[/bold blue]")
            settings.print_config()
        
        if config_path:
            console.print(f"\n📁 Configuration file: {settings.config_file_path}")
            
    except Exception as e:
        console.print(f"❌ [bold red]Configuration error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    console.print("\n🎙️  [bold blue]Transcription Service[/bold blue]")
    console.print("Version: 1.0.0-MVP")
    console.print("Author: Your Name")
    console.print("License: MIT")


if __name__ == '__main__':
    cli()