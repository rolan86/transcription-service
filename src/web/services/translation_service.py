"""
Translation service using argos-translate for offline local translation.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading


class TranslationService:
    """
    Offline translation service using argos-translate.
    Models are downloaded and cached locally.
    """

    _instance = None
    _lock = threading.Lock()

    # Supported language pairs (from_code -> to_code)
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ru': 'Russian',
        'ar': 'Arabic',
    }

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._argos = None
        self._models_dir = self._get_models_dir()
        self._installed_packages = {}

    def _get_models_dir(self) -> Path:
        """Get the models directory, creating if needed."""
        models_dir = Path.home() / ".transcription" / "translation_models"
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir

    @property
    def argos(self):
        """Lazy import of argostranslate."""
        if self._argos is None:
            try:
                import argostranslate.package
                import argostranslate.translate
                self._argos = {
                    'package': argostranslate.package,
                    'translate': argostranslate.translate,
                }
                # Set custom data directory
                os.environ['ARGOS_TRANSLATE_PACKAGES_DIR'] = str(self._models_dir)
            except ImportError:
                raise ImportError(
                    "argostranslate is required for translation. "
                    "Install with: pip install argostranslate"
                )
        return self._argos

    def get_available_languages(self) -> List[Dict[str, str]]:
        """
        Get list of available target languages.

        Returns:
            List of language dictionaries with code and name
        """
        return [
            {'code': code, 'name': name}
            for code, name in self.SUPPORTED_LANGUAGES.items()
        ]

    def get_installed_packages(self) -> List[Dict[str, str]]:
        """
        Get list of installed translation packages.

        Returns:
            List of installed package info
        """
        try:
            installed = self.argos['package'].get_installed_packages()
            return [
                {
                    'from_code': pkg.from_code,
                    'to_code': pkg.to_code,
                    'from_name': pkg.from_name,
                    'to_name': pkg.to_name,
                }
                for pkg in installed
            ]
        except Exception:
            return []

    def ensure_package_installed(
        self,
        from_code: str,
        to_code: str,
    ) -> Dict[str, Any]:
        """
        Ensure a translation package is installed, downloading if necessary.

        Args:
            from_code: Source language code
            to_code: Target language code

        Returns:
            Dictionary with success status
        """
        try:
            # Check if already installed
            installed = self.argos['package'].get_installed_packages()
            for pkg in installed:
                if pkg.from_code == from_code and pkg.to_code == to_code:
                    return {'success': True, 'already_installed': True}

            # Update package index
            self.argos['package'].update_package_index()

            # Find and install package
            available = self.argos['package'].get_available_packages()
            package_to_install = None

            for pkg in available:
                if pkg.from_code == from_code and pkg.to_code == to_code:
                    package_to_install = pkg
                    break

            if not package_to_install:
                return {
                    'success': False,
                    'error': f'No translation package found for {from_code} -> {to_code}',
                }

            # Download and install
            download_path = package_to_install.download()
            self.argos['package'].install_from_path(download_path)

            return {'success': True, 'installed': True}

        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to install package: {str(e)}',
            }

    def translate(
        self,
        text: str,
        from_code: str,
        to_code: str,
        auto_install: bool = True,
    ) -> Dict[str, Any]:
        """
        Translate text from one language to another.

        Args:
            text: Text to translate
            from_code: Source language code
            to_code: Target language code
            auto_install: Automatically install package if not available

        Returns:
            Dictionary with translation result
        """
        if not text.strip():
            return {
                'success': False,
                'error': 'No text to translate',
            }

        if from_code == to_code:
            return {
                'success': True,
                'translated_text': text,
                'from_language': from_code,
                'to_language': to_code,
            }

        try:
            # Check/install package
            if auto_install:
                install_result = self.ensure_package_installed(from_code, to_code)
                if not install_result.get('success'):
                    return install_result

            # Get translation
            installed = self.argos['package'].get_installed_packages()
            translation = None

            for pkg in installed:
                if pkg.from_code == from_code and pkg.to_code == to_code:
                    translation = pkg.get_translation()
                    break

            if not translation:
                return {
                    'success': False,
                    'error': f'Translation package not available for {from_code} -> {to_code}',
                }

            # Perform translation
            translated_text = translation.translate(text)

            return {
                'success': True,
                'translated_text': translated_text,
                'from_language': from_code,
                'to_language': to_code,
                'from_name': self.SUPPORTED_LANGUAGES.get(from_code, from_code),
                'to_name': self.SUPPORTED_LANGUAGES.get(to_code, to_code),
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Translation failed: {str(e)}',
            }

    def is_available(self) -> bool:
        """Check if translation service is available."""
        try:
            _ = self.argos
            return True
        except ImportError:
            return False
