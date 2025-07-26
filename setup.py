"""Setup script for transcription service POC."""

from setuptools import setup, find_packages

setup(
    name="transcription-service",
    version="0.1.0-poc",
    description="Audio/Video transcription service using OpenAI Whisper",
    author="Your Name",
    python_requires=">=3.11",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "openai-whisper>=20231117",
        "pydub>=0.25.1",
        "ffmpeg-python>=0.2.0",
        "numpy>=1.24.0",
        "torch>=2.0.0",
        "librosa>=0.10.0",
        "soundfile>=0.12.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "transcribe-poc=poc.transcribe_poc:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
    ],
)