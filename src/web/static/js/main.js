/**
 * Main application controller for the transcription web UI.
 */

// Application state
const AppState = {
    mode: 'upload',  // 'upload' or 'record'
    isProcessing: false,
    currentJob: null,
    selectedFile: null,
    settings: {
        model: 'base',
        language: '',
        outputFormat: 'json',
        enableSpeakers: false,
        showTimestamps: false,
        showConfidence: false,
        useVocabulary: false,
    },
    result: null,
    speakerNames: {},  // Map of original speaker ID to custom name
};

// Vocabulary modal elements
let vocabModalElements = {};

// Translation modal elements
let translationModalElements = {};

// Cleanup modal elements
let cleanupModalElements = {};

// Analysis panel elements
let analysisElements = {};

// All Whisper-supported languages (99 languages)
const WHISPER_LANGUAGES = [
    { code: '', name: 'Auto-detect' },
    { code: 'en', name: 'English' },
    { code: 'zh', name: 'Chinese' },
    { code: 'de', name: 'German' },
    { code: 'es', name: 'Spanish' },
    { code: 'ru', name: 'Russian' },
    { code: 'ko', name: 'Korean' },
    { code: 'fr', name: 'French' },
    { code: 'ja', name: 'Japanese' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'tr', name: 'Turkish' },
    { code: 'pl', name: 'Polish' },
    { code: 'ca', name: 'Catalan' },
    { code: 'nl', name: 'Dutch' },
    { code: 'ar', name: 'Arabic' },
    { code: 'sv', name: 'Swedish' },
    { code: 'it', name: 'Italian' },
    { code: 'id', name: 'Indonesian' },
    { code: 'hi', name: 'Hindi' },
    { code: 'fi', name: 'Finnish' },
    { code: 'vi', name: 'Vietnamese' },
    { code: 'he', name: 'Hebrew' },
    { code: 'uk', name: 'Ukrainian' },
    { code: 'el', name: 'Greek' },
    { code: 'ms', name: 'Malay' },
    { code: 'cs', name: 'Czech' },
    { code: 'ro', name: 'Romanian' },
    { code: 'da', name: 'Danish' },
    { code: 'hu', name: 'Hungarian' },
    { code: 'ta', name: 'Tamil' },
    { code: 'no', name: 'Norwegian' },
    { code: 'th', name: 'Thai' },
    { code: 'ur', name: 'Urdu' },
    { code: 'hr', name: 'Croatian' },
    { code: 'bg', name: 'Bulgarian' },
    { code: 'lt', name: 'Lithuanian' },
    { code: 'la', name: 'Latin' },
    { code: 'mi', name: 'Maori' },
    { code: 'ml', name: 'Malayalam' },
    { code: 'cy', name: 'Welsh' },
    { code: 'sk', name: 'Slovak' },
    { code: 'te', name: 'Telugu' },
    { code: 'fa', name: 'Persian' },
    { code: 'lv', name: 'Latvian' },
    { code: 'bn', name: 'Bengali' },
    { code: 'sr', name: 'Serbian' },
    { code: 'az', name: 'Azerbaijani' },
    { code: 'sl', name: 'Slovenian' },
    { code: 'kn', name: 'Kannada' },
    { code: 'et', name: 'Estonian' },
    { code: 'mk', name: 'Macedonian' },
    { code: 'br', name: 'Breton' },
    { code: 'eu', name: 'Basque' },
    { code: 'is', name: 'Icelandic' },
    { code: 'hy', name: 'Armenian' },
    { code: 'ne', name: 'Nepali' },
    { code: 'mn', name: 'Mongolian' },
    { code: 'bs', name: 'Bosnian' },
    { code: 'kk', name: 'Kazakh' },
    { code: 'sq', name: 'Albanian' },
    { code: 'sw', name: 'Swahili' },
    { code: 'gl', name: 'Galician' },
    { code: 'mr', name: 'Marathi' },
    { code: 'pa', name: 'Punjabi' },
    { code: 'si', name: 'Sinhala' },
    { code: 'km', name: 'Khmer' },
    { code: 'sn', name: 'Shona' },
    { code: 'yo', name: 'Yoruba' },
    { code: 'so', name: 'Somali' },
    { code: 'af', name: 'Afrikaans' },
    { code: 'oc', name: 'Occitan' },
    { code: 'ka', name: 'Georgian' },
    { code: 'be', name: 'Belarusian' },
    { code: 'tg', name: 'Tajik' },
    { code: 'sd', name: 'Sindhi' },
    { code: 'gu', name: 'Gujarati' },
    { code: 'am', name: 'Amharic' },
    { code: 'yi', name: 'Yiddish' },
    { code: 'lo', name: 'Lao' },
    { code: 'uz', name: 'Uzbek' },
    { code: 'fo', name: 'Faroese' },
    { code: 'ht', name: 'Haitian Creole' },
    { code: 'ps', name: 'Pashto' },
    { code: 'tk', name: 'Turkmen' },
    { code: 'nn', name: 'Nynorsk' },
    { code: 'mt', name: 'Maltese' },
    { code: 'sa', name: 'Sanskrit' },
    { code: 'lb', name: 'Luxembourgish' },
    { code: 'my', name: 'Myanmar' },
    { code: 'bo', name: 'Tibetan' },
    { code: 'tl', name: 'Tagalog' },
    { code: 'mg', name: 'Malagasy' },
    { code: 'as', name: 'Assamese' },
    { code: 'tt', name: 'Tatar' },
    { code: 'haw', name: 'Hawaiian' },
    { code: 'ln', name: 'Lingala' },
    { code: 'ha', name: 'Hausa' },
    { code: 'ba', name: 'Bashkir' },
    { code: 'jw', name: 'Javanese' },
    { code: 'su', name: 'Sundanese' },
];

// Language dropdown state
let languageDropdownHighlightIndex = -1;

// DOM Elements
const elements = {};

// Modal state
let modalCallback = null;
let modalElements = {};
let speakerModalElements = {};

/**
 * Initialize the application.
 */
function initApp() {
    // Cache DOM elements
    cacheElements();

    // Load saved settings from localStorage
    loadSavedSettings();

    // Set up event listeners
    setupEventListeners();

    // Apply loaded settings to UI
    applySettingsToUI();

    // Initialize theme
    initTheme();

    // Initialize sub-modules
    initUploader();
    initRecorder();

    console.log('Transcription app initialized');
}

/**
 * Load saved settings from localStorage and apply to UI.
 */
function loadSavedSettings() {
    try {
        const saved = localStorage.getItem('transcription_settings');
        if (saved) {
            const settings = JSON.parse(saved);
            // Apply saved settings to AppState
            if (settings.enableSpeakers !== undefined) {
                AppState.settings.enableSpeakers = settings.enableSpeakers;
            }
            if (settings.showTimestamps !== undefined) {
                AppState.settings.showTimestamps = settings.showTimestamps;
            }
            if (settings.showConfidence !== undefined) {
                AppState.settings.showConfidence = settings.showConfidence;
            }
            if (settings.model) {
                AppState.settings.model = settings.model;
            }
            if (settings.outputFormat) {
                AppState.settings.outputFormat = settings.outputFormat;
            }
        }
    } catch (e) {
        console.warn('Failed to load saved settings:', e);
    }
}

/**
 * Save current settings to localStorage.
 */
function saveSettings() {
    try {
        const settings = {
            enableSpeakers: AppState.settings.enableSpeakers,
            showTimestamps: AppState.settings.showTimestamps,
            showConfidence: AppState.settings.showConfidence,
            model: AppState.settings.model,
            outputFormat: AppState.settings.outputFormat,
        };
        localStorage.setItem('transcription_settings', JSON.stringify(settings));
    } catch (e) {
        console.warn('Failed to save settings:', e);
    }
}

/**
 * Apply loaded settings to UI elements (called after cacheElements).
 */
function applySettingsToUI() {
    if (elements.enableSpeakers) {
        elements.enableSpeakers.checked = AppState.settings.enableSpeakers;
    }
    if (elements.showTimestamps) {
        elements.showTimestamps.checked = AppState.settings.showTimestamps;
    }
    if (elements.showConfidence) {
        elements.showConfidence.checked = AppState.settings.showConfidence;
    }
    if (elements.modelSelect) {
        elements.modelSelect.value = AppState.settings.model;
    }
    if (elements.formatSelect) {
        elements.formatSelect.value = AppState.settings.outputFormat;
    }
}

/**
 * Initialize theme from localStorage or system preference.
 */
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme) {
        setTheme(savedTheme);
    } else if (systemPrefersDark) {
        setTheme('dark');
    } else {
        setTheme('light');
    }
}

/**
 * Set the theme and update UI.
 */
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateThemeIcon(theme);
}

/**
 * Toggle between light and dark themes.
 */
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

/**
 * Update the theme toggle icon.
 */
function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        // Moon for light mode (click to go dark), Sun for dark mode (click to go light)
        icon.innerHTML = theme === 'light' ? '&#9790;' : '&#9728;';
    }
}

/**
 * Cache frequently used DOM elements.
 */
function cacheElements() {
    elements.modeBtns = document.querySelectorAll('.mode-btn');
    elements.uploadMode = document.getElementById('upload-mode');
    elements.urlMode = document.getElementById('url-mode');
    elements.recordMode = document.getElementById('record-mode');
    elements.modelSelect = document.getElementById('model-select');
    // Searchable language dropdown elements
    elements.languageSelectContainer = document.getElementById('language-select-container');
    elements.languageSelectTrigger = document.getElementById('language-select-trigger');
    elements.languageSelectedText = document.getElementById('language-selected-text');
    elements.languageDropdown = document.getElementById('language-dropdown');
    elements.languageSearch = document.getElementById('language-search');
    elements.languageOptions = document.getElementById('language-options');
    elements.formatSelect = document.getElementById('format-select');
    elements.enableSpeakers = document.getElementById('enable-speakers');
    elements.showTimestamps = document.getElementById('show-timestamps');
    elements.showConfidence = document.getElementById('show-confidence');
    elements.progressContainer = document.getElementById('progress-container');
    elements.progressFill = document.getElementById('progress-fill');
    elements.progressText = document.getElementById('progress-text');
    elements.resultsContainer = document.getElementById('results-container');
    elements.transcriptText = document.getElementById('transcript-text');
    elements.resultLanguage = document.getElementById('result-language');
    elements.resultConfidence = document.getElementById('result-confidence');
    elements.resultTime = document.getElementById('result-time');
    elements.copyBtn = document.getElementById('copy-btn');
    elements.downloadBtn = document.getElementById('download-btn');
    elements.exportBtn = document.getElementById('export-btn');
    elements.exportMenu = document.getElementById('export-menu');
    elements.speakerLegend = document.getElementById('speaker-legend');
    elements.legendItems = document.getElementById('legend-items');
    elements.newTranscriptionBtn = document.getElementById('new-transcription-btn');
    elements.errorContainer = document.getElementById('error-container');
    elements.errorMessage = document.getElementById('error-message');
    elements.errorDismiss = document.getElementById('error-dismiss');
    elements.liveTranscript = document.getElementById('live-transcript');
    elements.liveText = document.getElementById('live-text');
    elements.recordingActions = document.getElementById('recording-actions');
    elements.downloadAudioBtn = document.getElementById('download-audio-btn');
    elements.downloadVideoBtn = document.getElementById('download-video-btn');
    elements.newRecordingBtn = document.getElementById('new-recording-btn');
    elements.recordHint = document.getElementById('record-hint');

    // Screen recording elements
    elements.recordingModeSelector = document.getElementById('recording-mode-selector');
    elements.recordingModeBtns = document.querySelectorAll('.recording-mode-btn');
    elements.platformBanner = document.getElementById('platform-capability-banner');
    elements.platformBannerText = document.getElementById('platform-banner-text');
    elements.bannerDismiss = document.getElementById('banner-dismiss');
    elements.saveVideoToggle = document.getElementById('save-video-toggle');
    elements.saveVideoCheckbox = document.getElementById('save-video-checkbox');
    elements.videoAudioOptions = document.getElementById('video-audio-options');
    elements.videoAudioRadios = document.querySelectorAll('input[name="video-audio"]');
    elements.screenPreview = document.getElementById('screen-preview');
    elements.screenPreviewVideo = document.getElementById('screen-preview-video');

    // Modal elements
    modalElements.modal = document.getElementById('filename-modal');
    modalElements.title = document.getElementById('modal-title');
    modalElements.input = document.getElementById('filename-input');
    modalElements.extension = document.getElementById('filename-extension');
    modalElements.cancelBtn = document.getElementById('modal-cancel');
    modalElements.confirmBtn = document.getElementById('modal-confirm');

    // Speaker rename elements
    elements.renameSpeakersBtn = document.getElementById('rename-speakers-btn');
    speakerModalElements.modal = document.getElementById('speaker-modal');
    speakerModalElements.list = document.getElementById('speaker-rename-list');
    speakerModalElements.cancelBtn = document.getElementById('speaker-modal-cancel');
    speakerModalElements.confirmBtn = document.getElementById('speaker-modal-confirm');

    // Vocabulary elements
    elements.useVocabulary = document.getElementById('use-vocabulary');
    elements.vocabEditBtn = document.getElementById('vocab-edit-btn');
    vocabModalElements.modal = document.getElementById('vocabulary-modal');
    vocabModalElements.textarea = document.getElementById('vocabulary-textarea');
    vocabModalElements.count = document.getElementById('vocab-count');
    vocabModalElements.cancelBtn = document.getElementById('vocab-modal-cancel');
    vocabModalElements.saveBtn = document.getElementById('vocab-modal-save');

    // URL import elements
    elements.urlInput = document.getElementById('url-input');
    elements.urlFetchBtn = document.getElementById('url-fetch-btn');
    elements.urlPreview = document.getElementById('url-preview');
    elements.urlThumbnail = document.getElementById('url-thumbnail');
    elements.urlTitle = document.getElementById('url-title');
    elements.urlUploader = document.getElementById('url-uploader');
    elements.urlDuration = document.getElementById('url-duration');
    elements.urlClearBtn = document.getElementById('url-clear-btn');
    elements.urlTranscribeBtn = document.getElementById('url-transcribe-btn');

    // Translation elements
    elements.translateBtn = document.getElementById('translate-btn');
    translationModalElements.modal = document.getElementById('translation-modal');
    translationModalElements.fromSelect = document.getElementById('translate-from');
    translationModalElements.toSelect = document.getElementById('translate-to');
    translationModalElements.progress = document.getElementById('translation-progress');
    translationModalElements.progressFill = document.getElementById('translation-progress-fill');
    translationModalElements.progressText = document.getElementById('translation-progress-text');
    translationModalElements.result = document.getElementById('translation-result');
    translationModalElements.output = document.getElementById('translation-output');
    translationModalElements.cancelBtn = document.getElementById('translation-modal-cancel');
    translationModalElements.translateBtn = document.getElementById('translation-modal-translate');
    translationModalElements.copyBtn = document.getElementById('translation-modal-copy');

    // Cleanup elements
    elements.cleanupBtn = document.getElementById('cleanup-btn');
    cleanupModalElements.modal = document.getElementById('cleanup-modal');
    cleanupModalElements.providerSelect = document.getElementById('cleanup-provider');
    cleanupModalElements.providerStatus = document.getElementById('provider-status');
    cleanupModalElements.progress = document.getElementById('cleanup-progress');
    cleanupModalElements.progressFill = document.getElementById('cleanup-progress-fill');
    cleanupModalElements.progressText = document.getElementById('cleanup-progress-text');
    cleanupModalElements.result = document.getElementById('cleanup-result');
    cleanupModalElements.stats = document.getElementById('cleanup-stats');
    cleanupModalElements.outputCleaned = document.getElementById('cleanup-output-cleaned');
    cleanupModalElements.outputOriginal = document.getElementById('cleanup-output-original');
    cleanupModalElements.outputDiff = document.getElementById('cleanup-output-diff');
    cleanupModalElements.cancelBtn = document.getElementById('cleanup-modal-cancel');
    cleanupModalElements.runBtn = document.getElementById('cleanup-modal-run');
    cleanupModalElements.applyBtn = document.getElementById('cleanup-modal-apply');
    cleanupModalElements.copyBtn = document.getElementById('cleanup-modal-copy');

    // Analysis elements
    elements.analyzeBtn = document.getElementById('analyze-btn');
    elements.analyzeMenu = document.getElementById('analyze-menu');
    analysisElements.panel = document.getElementById('analysis-panel');
    analysisElements.progress = document.getElementById('analysis-progress');
    analysisElements.progressFill = document.getElementById('analysis-progress-fill');
    analysisElements.progressText = document.getElementById('analysis-progress-text');
    analysisElements.content = document.getElementById('analysis-content');
    analysisElements.copyBtn = document.getElementById('copy-analysis-btn');
    analysisElements.exportBtn = document.getElementById('export-analysis-btn');
    analysisElements.closeBtn = document.getElementById('close-analysis-btn');

    // Advanced settings elements
    elements.maxFileSize = document.getElementById('max-file-size');
    elements.saveAdvancedSettings = document.getElementById('save-advanced-settings');
    elements.settingsStatus = document.getElementById('settings-status');
    elements.advancedSummary = document.getElementById('advanced-summary');
}

/**
 * Set up event listeners.
 */
function setupEventListeners() {
    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Mode switching
    elements.modeBtns.forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });

    // Settings changes
    elements.modelSelect.addEventListener('change', (e) => {
        AppState.settings.model = e.target.value;
        saveSettings();
    });

    // Initialize searchable language dropdown
    initLanguageDropdown();

    elements.formatSelect.addEventListener('change', (e) => {
        AppState.settings.outputFormat = e.target.value;
        saveSettings();
    });

    elements.enableSpeakers.addEventListener('change', (e) => {
        AppState.settings.enableSpeakers = e.target.checked;
        saveSettings();
    });

    elements.showTimestamps.addEventListener('change', (e) => {
        AppState.settings.showTimestamps = e.target.checked;
        saveSettings();
    });

    elements.showConfidence.addEventListener('change', (e) => {
        AppState.settings.showConfidence = e.target.checked;
        saveSettings();
    });

    // Result actions
    elements.copyBtn.addEventListener('click', copyTranscript);
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', downloadTranscript);
    }

    // Export menu
    if (elements.exportBtn) {
        elements.exportBtn.addEventListener('click', toggleExportMenu);
    }
    if (elements.exportMenu) {
        const items = elements.exportMenu.querySelectorAll('.dropdown-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                hideExportMenu();
                exportTranscript(item.dataset.format);
            });
        });
    }
    elements.newTranscriptionBtn.addEventListener('click', resetApp);

    // Error dismiss
    elements.errorDismiss.addEventListener('click', hideError);

    // Recording actions
    if (elements.downloadAudioBtn) {
        elements.downloadAudioBtn.addEventListener('click', () => {
            if (typeof downloadRecordedAudio === 'function') {
                downloadRecordedAudio();
            }
        });
    }

    if (elements.newRecordingBtn) {
        elements.newRecordingBtn.addEventListener('click', resetRecording);
    }

    // Video download button
    if (elements.downloadVideoBtn) {
        elements.downloadVideoBtn.addEventListener('click', () => {
            if (typeof downloadRecordedVideo === 'function') {
                downloadRecordedVideo();
            }
        });
    }

    // Screen recording mode events
    setupScreenRecordingEvents();

    // Modal events
    modalElements.cancelBtn.addEventListener('click', hideModal);
    modalElements.confirmBtn.addEventListener('click', confirmModal);
    modalElements.modal.addEventListener('click', (e) => {
        if (e.target === modalElements.modal) hideModal();
    });
    modalElements.input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') confirmModal();
    });

    // Speaker rename events
    elements.renameSpeakersBtn.addEventListener('click', showSpeakerRenameModal);
    speakerModalElements.cancelBtn.addEventListener('click', hideSpeakerRenameModal);
    speakerModalElements.confirmBtn.addEventListener('click', applySpeakerRenames);
    speakerModalElements.modal.addEventListener('click', (e) => {
        if (e.target === speakerModalElements.modal) hideSpeakerRenameModal();
    });

    // Vocabulary events
    if (elements.useVocabulary) {
        elements.useVocabulary.addEventListener('change', (e) => {
            AppState.settings.useVocabulary = e.target.checked;
        });
    }
    if (elements.vocabEditBtn) {
        elements.vocabEditBtn.addEventListener('click', showVocabularyModal);
    }
    if (vocabModalElements.cancelBtn) {
        vocabModalElements.cancelBtn.addEventListener('click', hideVocabularyModal);
    }
    if (vocabModalElements.saveBtn) {
        vocabModalElements.saveBtn.addEventListener('click', saveVocabulary);
    }
    if (vocabModalElements.modal) {
        vocabModalElements.modal.addEventListener('click', (e) => {
            if (e.target === vocabModalElements.modal) hideVocabularyModal();
        });
    }
    if (vocabModalElements.textarea) {
        vocabModalElements.textarea.addEventListener('input', updateVocabCount);
    }

    // URL import events
    if (elements.urlFetchBtn) {
        elements.urlFetchBtn.addEventListener('click', fetchUrlInfo);
    }
    if (elements.urlInput) {
        elements.urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') fetchUrlInfo();
        });
    }
    if (elements.urlClearBtn) {
        elements.urlClearBtn.addEventListener('click', clearUrlPreview);
    }
    if (elements.urlTranscribeBtn) {
        elements.urlTranscribeBtn.addEventListener('click', startUrlTranscription);
    }

    // Translation events
    if (elements.translateBtn) {
        elements.translateBtn.addEventListener('click', showTranslationModal);
    }
    if (translationModalElements.cancelBtn) {
        translationModalElements.cancelBtn.addEventListener('click', hideTranslationModal);
    }
    if (translationModalElements.translateBtn) {
        translationModalElements.translateBtn.addEventListener('click', performTranslation);
    }
    if (translationModalElements.copyBtn) {
        translationModalElements.copyBtn.addEventListener('click', copyTranslation);
    }
    if (translationModalElements.modal) {
        translationModalElements.modal.addEventListener('click', (e) => {
            if (e.target === translationModalElements.modal) hideTranslationModal();
        });
    }

    // Cleanup events
    if (elements.cleanupBtn) {
        elements.cleanupBtn.addEventListener('click', showCleanupModal);
    }
    if (cleanupModalElements.cancelBtn) {
        cleanupModalElements.cancelBtn.addEventListener('click', hideCleanupModal);
    }
    if (cleanupModalElements.runBtn) {
        cleanupModalElements.runBtn.addEventListener('click', performCleanup);
    }
    if (cleanupModalElements.applyBtn) {
        cleanupModalElements.applyBtn.addEventListener('click', applyCleanedTranscript);
    }
    if (cleanupModalElements.copyBtn) {
        cleanupModalElements.copyBtn.addEventListener('click', copyCleanedTranscript);
    }
    if (cleanupModalElements.modal) {
        cleanupModalElements.modal.addEventListener('click', (e) => {
            if (e.target === cleanupModalElements.modal) hideCleanupModal();
        });
        // Tab switching
        const tabs = cleanupModalElements.modal.querySelectorAll('.cleanup-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => switchCleanupTab(tab.dataset.view));
        });
    }

    // Analysis events
    if (elements.analyzeBtn) {
        elements.analyzeBtn.addEventListener('click', toggleAnalyzeMenu);
    }
    if (elements.analyzeMenu) {
        const items = elements.analyzeMenu.querySelectorAll('.dropdown-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                hideAnalyzeMenu();
                runAnalysis(item.dataset.action);
            });
        });
    }
    if (analysisElements.closeBtn) {
        analysisElements.closeBtn.addEventListener('click', hideAnalysisPanel);
    }
    if (analysisElements.copyBtn) {
        analysisElements.copyBtn.addEventListener('click', copyAnalysisResults);
    }
    if (analysisElements.exportBtn) {
        analysisElements.exportBtn.addEventListener('click', exportAnalysisResults);
    }
    // Close menus when clicking outside
    document.addEventListener('click', (e) => {
        if (elements.analyzeMenu && !elements.analyzeMenu.hidden) {
            if (!elements.analyzeBtn.contains(e.target) && !elements.analyzeMenu.contains(e.target)) {
                hideAnalyzeMenu();
            }
        }
        if (elements.exportMenu && !elements.exportMenu.hidden) {
            if (!elements.exportBtn.contains(e.target) && !elements.exportMenu.contains(e.target)) {
                hideExportMenu();
            }
        }
    });

    // Accordion panel events
    setupAccordionPanels();

    // Quick preset events
    setupPresetButtons();

    // Update summaries when settings change
    elements.modelSelect?.addEventListener('change', updateAccordionSummaries);
    // Note: Language dropdown updates summaries via selectLanguage()
    elements.formatSelect?.addEventListener('change', updateAccordionSummaries);
    elements.enableSpeakers?.addEventListener('change', updateAccordionSummaries);
    elements.useVocabulary?.addEventListener('change', updateAccordionSummaries);

    // Initial summary update
    updateAccordionSummaries();

    // Check speaker detection availability
    checkSpeakerDetectionStatus();

    // Advanced settings events
    if (elements.saveAdvancedSettings) {
        elements.saveAdvancedSettings.addEventListener('click', saveAdvancedSettings);
    }
    if (elements.maxFileSize) {
        elements.maxFileSize.addEventListener('change', updateAdvancedSummary);
    }

    // Load current server settings
    loadServerSettings();
}

/**
 * Switch between upload, url, and record modes.
 */
function switchMode(mode) {
    AppState.mode = mode;

    // Update button states
    elements.modeBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Show/hide mode content
    elements.uploadMode.classList.toggle('active', mode === 'upload');
    if (elements.urlMode) {
        elements.urlMode.classList.toggle('active', mode === 'url');
    }
    elements.recordMode.classList.toggle('active', mode === 'record');

    // Hide results when switching modes
    hideResults();
    hideProgress();
}

/**
 * Show progress indicator.
 */
function showProgress(text = 'Processing...', percent = 0) {
    elements.progressContainer.hidden = false;
    elements.progressText.textContent = text;
    elements.progressFill.style.width = `${percent}%`;
}

/**
 * Update progress.
 */
function updateProgress(text, percent) {
    elements.progressText.textContent = text;
    elements.progressFill.style.width = `${percent}%`;
}

/**
 * Hide progress indicator.
 */
function hideProgress() {
    elements.progressContainer.hidden = true;
    elements.progressFill.style.width = '0%';
}

/**
 * Show transcription results.
 */
function showResults(result) {
    AppState.result = result;

    // Check if speaker detection was enabled and has speakers
    const hasSpeakers = result.speaker_detection &&
                        result.speaker_detection.enabled &&
                        result.speaker_detection.speakers &&
                        result.speaker_detection.speakers.length > 0;

    // Show/hide rename speakers button
    elements.renameSpeakersBtn.hidden = !hasSpeakers;

    // Update speaker legend
    updateSpeakerLegend(hasSpeakers ? result.speaker_detection.speakers : []);

    // Determine how to display transcript
    const hasSegments = result.segments && result.segments.length > 0;
    const useTimestamps = AppState.settings.showTimestamps && hasSegments;
    const useConfidence = AppState.settings.showConfidence && hasSegments;
    const useSpeakers = hasSpeakers && hasSegments;

    // Format transcript based on enabled features
    if (useSpeakers || useConfidence) {
        // Use innerHTML for rich formatting
        elements.transcriptText.innerHTML = formatTranscriptRich(result.segments, {
            timestamps: useTimestamps,
            confidence: useConfidence,
            speakers: useSpeakers,
        });
    } else if (useTimestamps) {
        elements.transcriptText.textContent = formatTranscriptWithTimestamps(result.segments);
    } else {
        elements.transcriptText.textContent = result.text || '';
    }

    // Display metadata
    elements.resultLanguage.textContent = `Language: ${result.language || 'Unknown'}`;
    elements.resultConfidence.textContent = `Confidence: ${Math.round((result.confidence || 0) * 100)}%`;
    elements.resultTime.textContent = `Time: ${(result.processing_time || 0).toFixed(1)}s`;

    // Show container
    elements.resultsContainer.hidden = false;
    hideProgress();
}

/**
 * Format transcript with inline timestamps.
 */
function formatTranscriptWithTimestamps(segments) {
    return segments.map(seg => {
        const timestamp = formatTimestamp(seg.start);
        const text = (seg.text || '').trim();
        return `[${timestamp}] ${text}`;
    }).join('\n');
}

/**
 * Format seconds to MM:SS or HH:MM:SS format.
 */
function formatTimestamp(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hrs > 0) {
        return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format transcript with confidence highlighting.
 */
function formatTranscriptWithConfidence(segments, includeTimestamps) {
    return segments.map(seg => {
        const text = (seg.text || '').trim();
        const confidence = getConfidenceFromSegment(seg);
        const confidenceClass = getConfidenceClass(confidence);

        let line = '';
        if (includeTimestamps) {
            line += `[${formatTimestamp(seg.start)}] `;
        }

        // Wrap the segment text with confidence class
        line += `<span class="${confidenceClass}">${escapeHtml(text)}</span>`;
        return line;
    }).join('\n');
}

/**
 * Get confidence score from segment (convert avg_logprob to probability).
 */
function getConfidenceFromSegment(segment) {
    // Whisper returns avg_logprob which is negative
    // Convert to approximate probability using exp()
    if (segment.confidence !== undefined) {
        return segment.confidence;
    }
    if (segment.avg_logprob !== undefined) {
        // avg_logprob is typically between -1 and 0
        // exp(-0.5) ≈ 0.6, exp(-0.2) ≈ 0.82, exp(-0.1) ≈ 0.9
        return Math.exp(segment.avg_logprob);
    }
    return 1.0; // Default to high confidence if no data
}

/**
 * Get CSS class based on confidence level.
 */
function getConfidenceClass(confidence) {
    if (confidence >= 0.7) return 'confidence-high';
    if (confidence >= 0.5) return 'confidence-medium';
    return 'confidence-low';
}

/**
 * Escape HTML to prevent XSS.
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format transcript with rich features (speakers, timestamps, confidence).
 */
function formatTranscriptRich(segments, options) {
    return segments.map(seg => {
        const text = (seg.text || '').trim();
        let line = '';

        // Add speaker label if enabled
        if (options.speakers && seg.speaker) {
            const speakerName = getSpeakerDisplayName(seg.speaker);
            const speakerIndex = getSpeakerIndex(seg.speaker);
            line += `<span class="speaker-label speaker-${speakerIndex % 6}">${escapeHtml(speakerName)}</span>`;
        }

        // Add timestamp if enabled
        if (options.timestamps) {
            line += `[${formatTimestamp(seg.start)}] `;
        }

        // Add text with confidence highlighting if enabled
        if (options.confidence) {
            const confidence = getConfidenceFromSegment(seg);
            const confidenceClass = getConfidenceClass(confidence);
            line += `<span class="${confidenceClass}">${escapeHtml(text)}</span>`;
        } else {
            line += escapeHtml(text);
        }

        return line;
    }).join('\n');
}

/**
 * Get display name for speaker (custom name or original).
 */
function getSpeakerDisplayName(speakerId) {
    return AppState.speakerNames[speakerId] || speakerId;
}

/**
 * Get numeric index from speaker ID (e.g., SPEAKER_00 -> 0).
 */
function getSpeakerIndex(speakerId) {
    const match = speakerId.match(/\d+/);
    return match ? parseInt(match[0], 10) : 0;
}

/**
 * Show speaker rename modal.
 */
function showSpeakerRenameModal() {
    if (!AppState.result || !AppState.result.speaker_detection) return;

    const speakers = AppState.result.speaker_detection.speakers || [];
    const list = speakerModalElements.list;

    // Clear existing items
    list.innerHTML = '';

    // Create input for each speaker
    speakers.forEach((speaker, index) => {
        const item = document.createElement('div');
        item.className = 'speaker-rename-item';

        const label = document.createElement('span');
        label.className = `speaker-label speaker-${index % 6}`;
        label.textContent = speaker;

        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Enter custom name';
        input.dataset.speaker = speaker;
        input.value = AppState.speakerNames[speaker] || '';

        item.appendChild(label);
        item.appendChild(input);
        list.appendChild(item);
    });

    speakerModalElements.modal.hidden = false;
}

/**
 * Hide speaker rename modal.
 */
function hideSpeakerRenameModal() {
    speakerModalElements.modal.hidden = true;
}

/**
 * Apply speaker renames and refresh display.
 */
function applySpeakerRenames() {
    const inputs = speakerModalElements.list.querySelectorAll('input');

    inputs.forEach(input => {
        const speaker = input.dataset.speaker;
        const customName = input.value.trim();

        if (customName) {
            AppState.speakerNames[speaker] = customName;
        } else {
            delete AppState.speakerNames[speaker];
        }
    });

    hideSpeakerRenameModal();

    // Refresh the display with new names
    if (AppState.result) {
        showResults(AppState.result);
    }
}

/**
 * Hide results.
 */
function hideResults() {
    elements.resultsContainer.hidden = true;
    if (elements.speakerLegend) {
        elements.speakerLegend.hidden = true;
    }
    AppState.result = null;
}

/**
 * Show error message.
 * @param {string} message - The error message to display
 * @param {boolean} showSettingsLink - Whether to show a link to open settings
 */
function showError(message, showSettingsLink = false) {
    if (showSettingsLink) {
        elements.errorMessage.innerHTML = `${message} <a href="#" class="settings-link" onclick="openSettings(); return false;">Open Settings</a>`;
    } else {
        elements.errorMessage.textContent = message;
    }
    elements.errorContainer.hidden = false;
}

/**
 * Hide error message.
 */
function hideError() {
    elements.errorContainer.hidden = true;
}

/**
 * Show filename modal for downloads.
 */
function showModal(title, defaultName, extension, callback) {
    modalElements.title.textContent = title;
    modalElements.input.value = defaultName;
    modalElements.extension.textContent = extension;
    modalCallback = callback;
    modalElements.modal.hidden = false;
    modalElements.input.focus();
    modalElements.input.select();
}

/**
 * Hide filename modal.
 */
function hideModal() {
    modalElements.modal.hidden = true;
    modalCallback = null;
}

/**
 * Confirm modal and trigger callback with filename.
 */
function confirmModal() {
    const filename = modalElements.input.value.trim();
    if (filename && modalCallback) {
        const extension = modalElements.extension.textContent;
        modalCallback(filename + extension);
    }
    hideModal();
}

/**
 * Copy transcript to clipboard.
 */
async function copyTranscript() {
    if (!AppState.result?.text) return;

    try {
        await navigator.clipboard.writeText(AppState.result.text);
        elements.copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            elements.copyBtn.textContent = 'Copy Text';
        }, 2000);
    } catch (err) {
        showError('Failed to copy to clipboard');
    }
}

/**
 * Download transcript with filename prompt.
 */
function downloadTranscript() {
    if (!AppState.result?.text) return;

    const format = AppState.settings.outputFormat;
    let extension = '.txt';

    if (format === 'json') {
        extension = '.json';
    } else if (format === 'srt' || format === 'vtt') {
        extension = '.' + format;
    }

    // Generate default filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const defaultName = `transcript_${timestamp}`;

    // Show modal to get filename
    showModal('Save Transcript', defaultName, extension, (filename) => {
        performTranscriptDownload(filename);
    });
}

/**
 * Perform the actual transcript download.
 */
function performTranscriptDownload(filename) {
    const format = AppState.settings.outputFormat;
    let content = AppState.result.text;
    let mimeType = 'text/plain';

    if (format === 'json') {
        content = JSON.stringify(AppState.result, null, 2);
        mimeType = 'application/json';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Reset the application for a new transcription.
 */
function resetApp() {
    hideResults();
    hideError();
    hideProgress();

    // Reset file input
    if (typeof resetUploader === 'function') {
        resetUploader();
    }

    // Reset live transcript
    elements.liveTranscript.hidden = true;
    elements.liveText.textContent = '';

    AppState.isProcessing = false;
    AppState.currentJob = null;
    AppState.speakerNames = {};
    AppState.result = null;
}

/**
 * Show live transcript area.
 */
function showLiveTranscript() {
    elements.liveTranscript.hidden = false;
}

/**
 * Update live transcript text.
 */
function updateLiveTranscript(text, append = false) {
    if (append) {
        elements.liveText.textContent += ' ' + text;
    } else {
        elements.liveText.textContent = text;
    }
}

/**
 * Hide live transcript area.
 */
function hideLiveTranscript() {
    elements.liveTranscript.hidden = true;
}

/**
 * Show recording actions (download buttons).
 */
function showRecordingActions() {
    if (elements.recordingActions) {
        elements.recordingActions.hidden = false;
    }
}

/**
 * Hide recording actions.
 */
function hideRecordingActions() {
    if (elements.recordingActions) {
        elements.recordingActions.hidden = true;
    }
}

/**
 * Reset recording state for a new recording.
 */
function resetRecording() {
    hideResults();
    hideError();
    hideLiveTranscript();
    hideRecordingActions();

    // Reset live transcript text
    elements.liveText.textContent = '';

    // Reset timer display
    const timer = document.getElementById('record-timer');
    if (timer) {
        timer.textContent = '00:00';
    }

    // Hide screen preview
    if (elements.screenPreview) {
        elements.screenPreview.hidden = true;
    }
    if (elements.screenPreviewVideo) {
        elements.screenPreviewVideo.srcObject = null;
    }

    // Hide video download button
    if (elements.downloadVideoBtn) {
        elements.downloadVideoBtn.hidden = true;
    }
}

// ============================================================================
// URL Import Functions
// ============================================================================

// Store current URL info
let currentUrlInfo = null;

/**
 * Fetch information about a video URL.
 */
async function fetchUrlInfo() {
    const url = elements.urlInput.value.trim();
    if (!url) return;

    elements.urlFetchBtn.disabled = true;
    elements.urlFetchBtn.textContent = 'Fetching...';
    hideError();

    try {
        const response = await fetch(`/api/url/info?url=${encodeURIComponent(url)}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch video info');
        }

        const info = await response.json();
        currentUrlInfo = info;
        showUrlPreview(info);

    } catch (error) {
        showError(error.message);
        clearUrlPreview();
    } finally {
        elements.urlFetchBtn.disabled = false;
        elements.urlFetchBtn.textContent = 'Fetch Info';
    }
}

/**
 * Show URL preview with video information.
 */
function showUrlPreview(info) {
    elements.urlTitle.textContent = info.title || 'Unknown';
    elements.urlUploader.textContent = info.uploader || '';
    elements.urlDuration.textContent = info.duration ? formatDuration(info.duration) : '';

    if (info.thumbnail) {
        elements.urlThumbnail.style.backgroundImage = `url(${info.thumbnail})`;
    } else {
        elements.urlThumbnail.style.backgroundImage = '';
    }

    elements.urlPreview.hidden = false;
    elements.urlTranscribeBtn.disabled = false;
}

/**
 * Clear URL preview and reset state.
 */
function clearUrlPreview() {
    currentUrlInfo = null;
    elements.urlPreview.hidden = true;
    elements.urlTranscribeBtn.disabled = true;
    elements.urlThumbnail.style.backgroundImage = '';
}

/**
 * Start transcription from URL.
 */
async function startUrlTranscription() {
    if (!currentUrlInfo || AppState.isProcessing) return;

    const url = elements.urlInput.value.trim();
    if (!url) return;

    AppState.isProcessing = true;
    elements.urlTranscribeBtn.disabled = true;
    hideError();
    showProgress('Downloading and processing video...', 10);

    try {
        const formData = new FormData();
        formData.append('url', url);
        formData.append('output_format', AppState.settings.outputFormat);
        formData.append('model', AppState.settings.model);
        formData.append('enable_speakers', AppState.settings.enableSpeakers);
        formData.append('show_timestamps', AppState.settings.showTimestamps);
        formData.append('use_vocabulary', AppState.settings.useVocabulary);

        if (AppState.settings.language) {
            formData.append('language', AppState.settings.language);
        }

        const response = await fetch('/api/transcribe/url', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start transcription');
        }

        const data = await response.json();
        AppState.currentJob = data.job_id;

        updateProgress('Downloading audio...', 20);
        await pollJobStatus(data.job_id);

    } catch (error) {
        showError(error.message);
        hideProgress();
    } finally {
        AppState.isProcessing = false;
        elements.urlTranscribeBtn.disabled = false;
    }
}

/**
 * Format duration in seconds to MM:SS or HH:MM:SS.
 */
function formatDuration(seconds) {
    if (!seconds) return '';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
        return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${m}:${String(s).padStart(2, '0')}`;
}

// ============================================================================
// Vocabulary Management
// ============================================================================

/**
 * Show vocabulary modal and load current vocabulary.
 */
async function showVocabularyModal() {
    try {
        const response = await fetch('/api/vocabulary');
        if (response.ok) {
            const data = await response.json();
            vocabModalElements.textarea.value = data.vocabulary.join('\n');
            updateVocabCount();
        }
    } catch (err) {
        console.error('Failed to load vocabulary:', err);
        vocabModalElements.textarea.value = '';
    }

    vocabModalElements.modal.hidden = false;
    vocabModalElements.textarea.focus();
}

/**
 * Hide vocabulary modal.
 */
function hideVocabularyModal() {
    vocabModalElements.modal.hidden = true;
}

/**
 * Save vocabulary to server.
 */
async function saveVocabulary() {
    const vocabulary = vocabModalElements.textarea.value;

    try {
        const formData = new FormData();
        formData.append('vocabulary', vocabulary);

        const response = await fetch('/api/vocabulary', {
            method: 'PUT',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to save vocabulary');
        }

        const data = await response.json();
        console.log('Vocabulary saved:', data.count, 'terms');

        // Auto-enable vocabulary if terms were added
        if (data.count > 0 && elements.useVocabulary) {
            elements.useVocabulary.checked = true;
            AppState.settings.useVocabulary = true;
        }

        hideVocabularyModal();
    } catch (err) {
        console.error('Failed to save vocabulary:', err);
        showError('Failed to save vocabulary');
    }
}

/**
 * Update vocabulary term count display.
 */
function updateVocabCount() {
    const text = vocabModalElements.textarea.value;
    const terms = text.split('\n').filter(line => line.trim()).length;
    vocabModalElements.count.textContent = `${terms} term${terms !== 1 ? 's' : ''}`;
}

// ============================================================================
// Translation Functions
// ============================================================================

// Store current translation
let currentTranslation = null;

/**
 * Show translation modal and load available languages.
 */
async function showTranslationModal() {
    if (!AppState.result?.text) {
        showError('No transcript to translate');
        return;
    }

    // Reset modal state
    translationModalElements.progress.hidden = true;
    translationModalElements.result.hidden = true;
    translationModalElements.translateBtn.hidden = false;
    translationModalElements.copyBtn.hidden = true;
    currentTranslation = null;

    // Load available languages
    try {
        const response = await fetch('/api/translate/languages');
        if (response.ok) {
            const data = await response.json();
            populateLanguageSelects(data.languages);
        }
    } catch (err) {
        console.error('Failed to load translation languages:', err);
    }

    // Set source language from detected language
    if (AppState.result?.language) {
        const detectedLang = AppState.result.language.toLowerCase();
        const fromSelect = translationModalElements.fromSelect;
        for (let option of fromSelect.options) {
            if (option.value === detectedLang) {
                fromSelect.value = detectedLang;
                break;
            }
        }
    }

    translationModalElements.modal.hidden = false;
}

/**
 * Populate language select dropdowns.
 */
function populateLanguageSelects(languages) {
    const fromSelect = translationModalElements.fromSelect;
    const toSelect = translationModalElements.toSelect;

    // Clear existing options
    fromSelect.innerHTML = '';
    toSelect.innerHTML = '<option value="">Select language...</option>';

    // Add language options
    languages.forEach(lang => {
        const fromOption = document.createElement('option');
        fromOption.value = lang.code;
        fromOption.textContent = lang.name;
        fromSelect.appendChild(fromOption);

        const toOption = document.createElement('option');
        toOption.value = lang.code;
        toOption.textContent = lang.name;
        toSelect.appendChild(toOption);
    });

    // Set English as default source
    fromSelect.value = 'en';
}

/**
 * Hide translation modal.
 */
function hideTranslationModal() {
    translationModalElements.modal.hidden = true;
}

/**
 * Perform translation of the transcript.
 */
async function performTranslation() {
    const fromLang = translationModalElements.fromSelect.value;
    const toLang = translationModalElements.toSelect.value;

    if (!toLang) {
        showError('Please select a target language');
        return;
    }

    if (fromLang === toLang) {
        showError('Source and target languages must be different');
        return;
    }

    if (!AppState.result?.text) {
        showError('No transcript to translate');
        return;
    }

    // Show progress
    translationModalElements.progress.hidden = false;
    translationModalElements.result.hidden = true;
    translationModalElements.translateBtn.disabled = true;
    translationModalElements.progressFill.style.width = '30%';
    translationModalElements.progressText.textContent = 'Preparing translation...';

    try {
        // Note: First translation may download the model, which can take time
        translationModalElements.progressText.textContent = 'Translating (may download model on first use)...';
        translationModalElements.progressFill.style.width = '50%';

        const formData = new FormData();
        formData.append('text', AppState.result.text);
        formData.append('from_language', fromLang);
        formData.append('to_language', toLang);

        const response = await fetch('/api/translate', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Translation failed');
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Translation failed');
        }

        translationModalElements.progressFill.style.width = '100%';
        translationModalElements.progressText.textContent = 'Translation complete!';

        // Show result
        currentTranslation = data.translated_text;
        translationModalElements.output.textContent = data.translated_text;
        translationModalElements.result.hidden = false;
        translationModalElements.translateBtn.hidden = true;
        translationModalElements.copyBtn.hidden = false;

        // Hide progress after a moment
        setTimeout(() => {
            translationModalElements.progress.hidden = true;
        }, 1000);

    } catch (error) {
        showError(error.message);
        translationModalElements.progress.hidden = true;
    } finally {
        translationModalElements.translateBtn.disabled = false;
    }
}

/**
 * Copy translation to clipboard.
 */
async function copyTranslation() {
    if (!currentTranslation) return;

    try {
        await navigator.clipboard.writeText(currentTranslation);
        translationModalElements.copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            translationModalElements.copyBtn.textContent = 'Copy Translation';
        }, 2000);
    } catch (err) {
        showError('Failed to copy to clipboard');
    }
}

// ============================================================================
// AI Cleanup Functions
// ============================================================================

// Store current cleanup result
let currentCleanupResult = null;

/**
 * Show cleanup modal and load available providers.
 */
async function showCleanupModal() {
    if (!AppState.result?.text) {
        showError('No transcript to clean up');
        return;
    }

    // Reset modal state
    cleanupModalElements.progress.hidden = true;
    cleanupModalElements.result.hidden = true;
    cleanupModalElements.runBtn.hidden = false;
    cleanupModalElements.applyBtn.hidden = true;
    cleanupModalElements.copyBtn.hidden = true;
    cleanupModalElements.runBtn.disabled = false;
    currentCleanupResult = null;

    // Load available providers
    try {
        const response = await fetch('/api/ai/providers');
        if (response.ok) {
            const data = await response.json();
            populateProviderSelect(data);
        } else {
            cleanupModalElements.providerStatus.textContent = 'Failed to load providers';
            cleanupModalElements.providerStatus.className = 'provider-status error';
        }
    } catch (err) {
        console.error('Failed to load AI providers:', err);
        cleanupModalElements.providerStatus.innerHTML = 'No providers available. <a href="#" class="settings-link" onclick="openSettings(); return false;">Open Settings</a>';
        cleanupModalElements.providerStatus.className = 'provider-status error';
    }

    cleanupModalElements.modal.hidden = false;
}

/**
 * Populate provider select dropdown.
 */
function populateProviderSelect(data) {
    const select = cleanupModalElements.providerSelect;
    select.innerHTML = '<option value="">Auto (use default)</option>';

    const providers = data.providers || {};
    const available = data.available_providers || [];

    Object.entries(providers).forEach(([key, info]) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = info.name;
        option.disabled = !info.available;
        if (!info.available) {
            option.textContent += ' (not configured)';
        }
        select.appendChild(option);
    });

    // Update status
    if (available.length > 0) {
        cleanupModalElements.providerStatus.textContent = `${available.length} provider(s) available`;
        cleanupModalElements.providerStatus.className = 'provider-status success';
    } else {
        cleanupModalElements.providerStatus.innerHTML = 'No providers configured. <a href="#" class="settings-link" onclick="openSettings(); return false;">Open Settings</a>';
        cleanupModalElements.providerStatus.className = 'provider-status error';
        cleanupModalElements.runBtn.disabled = true;
    }
}

/**
 * Hide cleanup modal.
 */
function hideCleanupModal() {
    cleanupModalElements.modal.hidden = true;
}

/**
 * Perform AI cleanup on the transcript.
 */
async function performCleanup() {
    if (!AppState.result?.text) {
        showError('No transcript to clean up');
        return;
    }

    const provider = cleanupModalElements.providerSelect.value;

    // Show progress
    cleanupModalElements.progress.hidden = false;
    cleanupModalElements.result.hidden = true;
    cleanupModalElements.runBtn.disabled = true;
    cleanupModalElements.progressFill.style.width = '30%';
    cleanupModalElements.progressText.textContent = 'Sending to AI...';

    try {
        cleanupModalElements.progressFill.style.width = '50%';
        cleanupModalElements.progressText.textContent = 'Processing transcript...';

        const formData = new FormData();
        formData.append('transcript', AppState.result.text);
        if (provider) {
            formData.append('provider', provider);
        }

        const response = await fetch('/api/ai/cleanup', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Cleanup failed');
        }

        const data = await response.json();
        currentCleanupResult = data;

        cleanupModalElements.progressFill.style.width = '100%';
        cleanupModalElements.progressText.textContent = 'Cleanup complete!';

        // Show result
        displayCleanupResult(data);

        // Hide progress after a moment
        setTimeout(() => {
            cleanupModalElements.progress.hidden = true;
        }, 1000);

    } catch (error) {
        showError(error.message);
        cleanupModalElements.progress.hidden = true;
    } finally {
        cleanupModalElements.runBtn.disabled = false;
    }
}

/**
 * Display cleanup result in the modal.
 */
function displayCleanupResult(data) {
    // Update stats
    const stats = cleanupModalElements.stats;
    const wordsRemoved = data.word_count_original - data.word_count_cleaned;
    const percentReduced = data.word_count_original > 0
        ? Math.round((wordsRemoved / data.word_count_original) * 100)
        : 0;

    stats.innerHTML = `
        <span class="stat">Filler words removed: <strong>${data.filler_words_removed}</strong></span>
        <span class="stat">Words: ${data.word_count_original} → ${data.word_count_cleaned}</span>
        <span class="stat">Reduced by: ${percentReduced}%</span>
        <span class="stat provider-used">Provider: ${data.provider_used || 'unknown'}</span>
    `;

    // Display cleaned text
    cleanupModalElements.outputCleaned.textContent = data.cleaned;

    // Display original text
    cleanupModalElements.outputOriginal.textContent = data.original;

    // Generate diff view
    generateDiffView(data.original, data.cleaned);

    // Show result panel and buttons
    cleanupModalElements.result.hidden = false;
    cleanupModalElements.runBtn.hidden = true;
    cleanupModalElements.applyBtn.hidden = false;
    cleanupModalElements.copyBtn.hidden = false;

    // Reset to cleaned tab
    switchCleanupTab('cleaned');
}

/**
 * Generate a visual diff between original and cleaned text.
 */
function generateDiffView(original, cleaned) {
    const originalWords = original.split(/\s+/);
    const cleanedWords = cleaned.split(/\s+/);

    // Simple word-level diff visualization
    const diffContainer = cleanupModalElements.outputDiff;
    diffContainer.innerHTML = '';

    // Use a simple LCS-based diff approach
    const diff = computeWordDiff(originalWords, cleanedWords);

    diff.forEach(item => {
        const span = document.createElement('span');
        span.className = `diff-${item.type}`;
        span.textContent = item.text + ' ';
        diffContainer.appendChild(span);
    });
}

/**
 * Compute word-level diff between two arrays of words.
 */
function computeWordDiff(original, cleaned) {
    const result = [];
    let i = 0;
    let j = 0;

    // Common filler words that are likely removed
    const fillerWords = new Set([
        'um', 'uh', 'umm', 'uhh', 'like', 'basically', 'actually',
        'literally', 'you', 'know', 'i', 'mean', 'so', 'kind', 'of', 'sort'
    ]);

    while (i < original.length || j < cleaned.length) {
        if (i >= original.length) {
            // Remaining cleaned words are additions
            result.push({ type: 'added', text: cleaned[j] });
            j++;
        } else if (j >= cleaned.length) {
            // Remaining original words are removals
            result.push({ type: 'removed', text: original[i] });
            i++;
        } else {
            const origWord = original[i].toLowerCase().replace(/[.,!?;:]/g, '');
            const cleanWord = cleaned[j].toLowerCase().replace(/[.,!?;:]/g, '');

            if (origWord === cleanWord) {
                result.push({ type: 'same', text: original[i] });
                i++;
                j++;
            } else if (fillerWords.has(origWord)) {
                result.push({ type: 'removed', text: original[i] });
                i++;
            } else {
                // Look ahead to see if this is a modification or removal
                let foundLater = false;
                for (let k = j; k < Math.min(j + 5, cleaned.length); k++) {
                    if (cleaned[k].toLowerCase().replace(/[.,!?;:]/g, '') === origWord) {
                        foundLater = true;
                        break;
                    }
                }

                if (foundLater) {
                    // Word appears later, so current clean word is new
                    result.push({ type: 'added', text: cleaned[j] });
                    j++;
                } else {
                    // Word was removed or changed
                    result.push({ type: 'removed', text: original[i] });
                    i++;
                }
            }
        }
    }

    return result;
}

/**
 * Switch between cleanup view tabs.
 */
function switchCleanupTab(view) {
    // Update tab buttons
    const tabs = cleanupModalElements.modal.querySelectorAll('.cleanup-tab');
    tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === view);
    });

    // Show/hide outputs
    cleanupModalElements.outputCleaned.hidden = view !== 'cleaned';
    cleanupModalElements.outputOriginal.hidden = view !== 'original';
    cleanupModalElements.outputDiff.hidden = view !== 'diff';
}

/**
 * Apply cleaned transcript to the main result.
 */
function applyCleanedTranscript() {
    if (!currentCleanupResult || !AppState.result) return;

    // Update the result text
    AppState.result.text = currentCleanupResult.cleaned;

    // Re-render the transcript display
    elements.transcriptText.textContent = currentCleanupResult.cleaned;

    // Close the modal
    hideCleanupModal();

    // Show confirmation
    showTemporaryMessage('Cleaned transcript applied!');
}

/**
 * Copy cleaned transcript to clipboard.
 */
async function copyCleanedTranscript() {
    if (!currentCleanupResult?.cleaned) return;

    try {
        await navigator.clipboard.writeText(currentCleanupResult.cleaned);
        cleanupModalElements.copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            cleanupModalElements.copyBtn.textContent = 'Copy Cleaned';
        }, 2000);
    } catch (err) {
        showError('Failed to copy to clipboard');
    }
}

/**
 * Show a temporary message (toast-like notification).
 */
function showTemporaryMessage(message) {
    // Use the copy button approach
    const originalText = elements.copyBtn.textContent;
    elements.copyBtn.textContent = message;
    setTimeout(() => {
        elements.copyBtn.textContent = originalText;
    }, 2000);
}

// ============================================================================
// AI Analysis Functions
// ============================================================================

// Store current analysis result
let currentAnalysisResult = null;

/**
 * Toggle the analyze dropdown menu.
 */
function toggleAnalyzeMenu() {
    if (elements.analyzeMenu) {
        elements.analyzeMenu.hidden = !elements.analyzeMenu.hidden;
    }
}

/**
 * Hide the analyze dropdown menu.
 */
function hideAnalyzeMenu() {
    if (elements.analyzeMenu) {
        elements.analyzeMenu.hidden = true;
    }
}

/**
 * Toggle the export dropdown menu.
 */
function toggleExportMenu() {
    if (elements.exportMenu) {
        elements.exportMenu.hidden = !elements.exportMenu.hidden;
        // Close analyze menu if open
        if (elements.analyzeMenu) {
            elements.analyzeMenu.hidden = true;
        }
    }
}

/**
 * Hide the export dropdown menu.
 */
function hideExportMenu() {
    if (elements.exportMenu) {
        elements.exportMenu.hidden = true;
    }
}

/**
 * Export transcript in the specified format.
 */
function exportTranscript(format) {
    if (!AppState.result) {
        showError('No transcript to export');
        return;
    }

    let content = '';
    let filename = 'transcript';
    let mimeType = 'text/plain';

    switch (format) {
        case 'txt':
            content = AppState.result.text || '';
            filename += '.txt';
            break;

        case 'json':
            content = JSON.stringify(AppState.result, null, 2);
            filename += '.json';
            mimeType = 'application/json';
            break;

        case 'srt':
            content = generateSRT(AppState.result);
            filename += '.srt';
            break;

        case 'vtt':
            content = generateVTT(AppState.result);
            filename += '.vtt';
            mimeType = 'text/vtt';
            break;

        case 'md':
            content = generateMarkdown(AppState.result);
            filename += '.md';
            mimeType = 'text/markdown';
            break;

        default:
            content = AppState.result.text || '';
            filename += '.txt';
    }

    downloadFile(content, filename, mimeType);
}

/**
 * Generate SRT format from result.
 */
function generateSRT(result) {
    if (!result.segments || result.segments.length === 0) {
        return result.text || '';
    }

    return result.segments.map((seg, i) => {
        const start = formatSRTTime(seg.start);
        const end = formatSRTTime(seg.end);
        return `${i + 1}\n${start} --> ${end}\n${seg.text.trim()}\n`;
    }).join('\n');
}

/**
 * Generate VTT format from result.
 */
function generateVTT(result) {
    if (!result.segments || result.segments.length === 0) {
        return `WEBVTT\n\n${result.text || ''}`;
    }

    const cues = result.segments.map(seg => {
        const start = formatVTTTime(seg.start);
        const end = formatVTTTime(seg.end);
        return `${start} --> ${end}\n${seg.text.trim()}`;
    }).join('\n\n');

    return `WEBVTT\n\n${cues}`;
}

/**
 * Generate Markdown format from result.
 */
function generateMarkdown(result) {
    let md = '# Transcription\n\n';

    if (result.language) {
        md += `**Language:** ${result.language}\n\n`;
    }

    if (result.speakers && result.speakers.length > 0) {
        md += '## Transcript\n\n';
        result.segments?.forEach(seg => {
            const speaker = seg.speaker ? `**${AppState.speakerNames[seg.speaker] || seg.speaker}:** ` : '';
            md += `${speaker}${seg.text.trim()}\n\n`;
        });
    } else {
        md += result.text || '';
    }

    return md;
}

/**
 * Format time for SRT (HH:MM:SS,mmm).
 */
function formatSRTTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.round((seconds % 1) * 1000);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

/**
 * Format time for VTT (HH:MM:SS.mmm).
 */
function formatVTTTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.round((seconds % 1) * 1000);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
}

/**
 * Download a file with the given content.
 */
function downloadFile(content, filename, mimeType = 'text/plain') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Run analysis based on the selected action.
 */
async function runAnalysis(action) {
    if (!AppState.result?.text) {
        showError('No transcript to analyze');
        return;
    }

    // Show analysis panel with progress
    showAnalysisPanel();
    showAnalysisProgress('Analyzing transcript...');

    const endpoint = getAnalysisEndpoint(action);
    const formData = new FormData();
    formData.append('transcript', AppState.result.text);

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }

        const data = await response.json();
        currentAnalysisResult = { action, data };

        hideAnalysisProgress();
        displayAnalysisResult(action, data);

    } catch (error) {
        showError(error.message);
        hideAnalysisPanel();
    }
}

/**
 * Get API endpoint for analysis action.
 */
function getAnalysisEndpoint(action) {
    const endpoints = {
        'summary': '/api/ai/extract/summary',
        'key-points': '/api/ai/extract/key-points',
        'action-items': '/api/ai/extract/action-items',
        'entities': '/api/ai/extract/entities',
        'meeting-notes': '/api/ai/extract/meeting-notes',
        'full-analysis': '/api/ai/extract/analyze',
    };
    return endpoints[action] || endpoints['summary'];
}

/**
 * Show the analysis panel.
 */
function showAnalysisPanel() {
    if (analysisElements.panel) {
        analysisElements.panel.hidden = false;
    }
}

/**
 * Hide the analysis panel.
 */
function hideAnalysisPanel() {
    if (analysisElements.panel) {
        analysisElements.panel.hidden = true;
    }
    currentAnalysisResult = null;
}

/**
 * Show analysis progress.
 */
function showAnalysisProgress(text) {
    if (analysisElements.progress) {
        analysisElements.progress.hidden = false;
        analysisElements.progressText.textContent = text;
        analysisElements.progressFill.style.width = '50%';
    }
    if (analysisElements.content) {
        analysisElements.content.innerHTML = '';
    }
}

/**
 * Hide analysis progress.
 */
function hideAnalysisProgress() {
    if (analysisElements.progress) {
        analysisElements.progress.hidden = true;
    }
}

/**
 * Display analysis result in the panel.
 */
function displayAnalysisResult(action, data) {
    const content = analysisElements.content;
    if (!content) return;

    content.innerHTML = '';

    switch (action) {
        case 'summary':
            content.appendChild(createAnalysisSection('Summary', data.summary, 'text'));
            break;

        case 'key-points':
            content.appendChild(createAnalysisSection('Key Points', data.key_points, 'list'));
            break;

        case 'action-items':
            content.appendChild(createAnalysisSection('Action Items', data.action_items, 'action-items'));
            break;

        case 'entities':
            content.appendChild(createAnalysisSection('Entities', data.entities, 'entities'));
            break;

        case 'meeting-notes':
            content.appendChild(createAnalysisSection('Meeting Notes', data.meeting_notes, 'markdown'));
            break;

        case 'full-analysis':
            if (data.summary) {
                content.appendChild(createAnalysisSection('Summary', data.summary, 'text'));
            }
            if (data.key_points && data.key_points.length > 0) {
                content.appendChild(createAnalysisSection('Key Points', data.key_points, 'list'));
            }
            if (data.action_items && data.action_items.length > 0) {
                content.appendChild(createAnalysisSection('Action Items', data.action_items, 'action-items'));
            }
            if (data.topics && data.topics.length > 0) {
                content.appendChild(createAnalysisSection('Topics', data.topics, 'topics'));
            }
            if (data.entities) {
                content.appendChild(createAnalysisSection('Entities', data.entities, 'entities'));
            }
            break;
    }

    // Add provider info
    if (data.provider_used) {
        const providerInfo = document.createElement('div');
        providerInfo.className = 'analysis-provider';
        providerInfo.textContent = `Analyzed by: ${data.provider_used}`;
        content.appendChild(providerInfo);
    }
}

/**
 * Create an analysis section element.
 */
function createAnalysisSection(title, data, type) {
    const section = document.createElement('div');
    section.className = 'analysis-section';

    const header = document.createElement('h4');
    header.textContent = title;
    section.appendChild(header);

    const body = document.createElement('div');
    body.className = 'analysis-section-body';

    switch (type) {
        case 'text':
            body.textContent = data || 'No data available';
            break;

        case 'markdown':
            body.innerHTML = simpleMarkdownToHtml(data || 'No data available');
            break;

        case 'list':
            if (Array.isArray(data) && data.length > 0) {
                const ul = document.createElement('ul');
                data.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item;
                    ul.appendChild(li);
                });
                body.appendChild(ul);
            } else {
                body.textContent = 'No items found';
            }
            break;

        case 'action-items':
            if (Array.isArray(data) && data.length > 0) {
                const ul = document.createElement('ul');
                ul.className = 'action-items-list';
                data.forEach(item => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span class="action-text">${escapeHtml(item.action)}</span>`;
                    if (item.assignee) {
                        li.innerHTML += ` <span class="action-assignee">@${escapeHtml(item.assignee)}</span>`;
                    }
                    ul.appendChild(li);
                });
                body.appendChild(ul);
            } else {
                body.textContent = 'No action items found';
            }
            break;

        case 'topics':
            if (Array.isArray(data) && data.length > 0) {
                const ul = document.createElement('ul');
                ul.className = 'topics-list';
                data.forEach(item => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span class="topic-name">${escapeHtml(item.topic)}</span>`;
                    if (item.relevance) {
                        li.innerHTML += ` <span class="topic-relevance relevance-${item.relevance}">${item.relevance}</span>`;
                    }
                    ul.appendChild(li);
                });
                body.appendChild(ul);
            } else {
                body.textContent = 'No topics found';
            }
            break;

        case 'entities':
            if (data && typeof data === 'object') {
                const categories = ['people', 'organizations', 'locations', 'dates', 'products'];
                let hasEntities = false;

                categories.forEach(category => {
                    if (data[category] && data[category].length > 0) {
                        hasEntities = true;
                        const catDiv = document.createElement('div');
                        catDiv.className = 'entity-category';
                        catDiv.innerHTML = `<strong>${capitalizeFirst(category)}:</strong> ${data[category].map(e => escapeHtml(e)).join(', ')}`;
                        body.appendChild(catDiv);
                    }
                });

                if (!hasEntities) {
                    body.textContent = 'No entities found';
                }
            } else {
                body.textContent = 'No entities found';
            }
            break;

        default:
            body.textContent = JSON.stringify(data, null, 2);
    }

    section.appendChild(body);
    return section;
}

/**
 * Simple markdown to HTML converter.
 */
function simpleMarkdownToHtml(markdown) {
    return markdown
        .replace(/^### (.*$)/gm, '<h5>$1</h5>')
        .replace(/^## (.*$)/gm, '<h4>$1</h4>')
        .replace(/^# (.*$)/gm, '<h3>$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^- (.*$)/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^(.+)$/gm, '<p>$1</p>')
        .replace(/<p><h/g, '<h')
        .replace(/<\/h(\d)><\/p>/g, '</h$1>')
        .replace(/<p><ul>/g, '<ul>')
        .replace(/<\/ul><\/p>/g, '</ul>');
}

/**
 * Capitalize first letter.
 */
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Copy analysis results to clipboard.
 */
async function copyAnalysisResults() {
    if (!currentAnalysisResult) return;

    const text = formatAnalysisAsText(currentAnalysisResult.action, currentAnalysisResult.data);

    try {
        await navigator.clipboard.writeText(text);
        analysisElements.copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            analysisElements.copyBtn.textContent = 'Copy';
        }, 2000);
    } catch (err) {
        showError('Failed to copy to clipboard');
    }
}

/**
 * Export analysis results as Markdown.
 */
function exportAnalysisResults() {
    if (!currentAnalysisResult) return;

    const markdown = formatAnalysisAsMarkdown(currentAnalysisResult.action, currentAnalysisResult.data);
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const filename = `analysis_${currentAnalysisResult.action}_${timestamp}.md`;

    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Format analysis as plain text.
 */
function formatAnalysisAsText(action, data) {
    let text = '';

    switch (action) {
        case 'summary':
            text = `Summary:\n${data.summary}`;
            break;
        case 'key-points':
            text = 'Key Points:\n' + data.key_points.map((p, i) => `${i + 1}. ${p}`).join('\n');
            break;
        case 'action-items':
            text = 'Action Items:\n' + data.action_items.map((a, i) => {
                let item = `${i + 1}. ${a.action}`;
                if (a.assignee) item += ` (@${a.assignee})`;
                return item;
            }).join('\n');
            break;
        case 'meeting-notes':
            text = data.meeting_notes;
            break;
        case 'full-analysis':
            const parts = [];
            if (data.summary) parts.push(`Summary:\n${data.summary}`);
            if (data.key_points?.length) parts.push('Key Points:\n' + data.key_points.map((p, i) => `${i + 1}. ${p}`).join('\n'));
            if (data.action_items?.length) parts.push('Action Items:\n' + data.action_items.map((a, i) => `${i + 1}. ${a.action}${a.assignee ? ` (@${a.assignee})` : ''}`).join('\n'));
            text = parts.join('\n\n');
            break;
        default:
            text = JSON.stringify(data, null, 2);
    }

    return text;
}

/**
 * Format analysis as Markdown.
 */
function formatAnalysisAsMarkdown(action, data) {
    let md = `# Transcript Analysis\n\n`;
    md += `*Generated: ${new Date().toLocaleString()}*\n\n`;

    switch (action) {
        case 'summary':
            md += `## Summary\n\n${data.summary}\n`;
            break;
        case 'key-points':
            md += `## Key Points\n\n`;
            data.key_points.forEach((p, i) => {
                md += `${i + 1}. ${p}\n`;
            });
            break;
        case 'action-items':
            md += `## Action Items\n\n`;
            data.action_items.forEach((a, i) => {
                md += `- [ ] ${a.action}`;
                if (a.assignee) md += ` *(${a.assignee})*`;
                md += '\n';
            });
            break;
        case 'meeting-notes':
            md += data.meeting_notes;
            break;
        case 'full-analysis':
            if (data.summary) {
                md += `## Summary\n\n${data.summary}\n\n`;
            }
            if (data.key_points?.length) {
                md += `## Key Points\n\n`;
                data.key_points.forEach((p, i) => {
                    md += `${i + 1}. ${p}\n`;
                });
                md += '\n';
            }
            if (data.action_items?.length) {
                md += `## Action Items\n\n`;
                data.action_items.forEach(a => {
                    md += `- [ ] ${a.action}`;
                    if (a.assignee) md += ` *(${a.assignee})*`;
                    md += '\n';
                });
                md += '\n';
            }
            if (data.topics?.length) {
                md += `## Topics\n\n`;
                data.topics.forEach(t => {
                    md += `- **${t.topic}** (${t.relevance})\n`;
                });
                md += '\n';
            }
            if (data.entities) {
                const cats = ['people', 'organizations', 'locations', 'dates', 'products'];
                const hasEntities = cats.some(c => data.entities[c]?.length > 0);
                if (hasEntities) {
                    md += `## Entities\n\n`;
                    cats.forEach(c => {
                        if (data.entities[c]?.length > 0) {
                            md += `- **${capitalizeFirst(c)}:** ${data.entities[c].join(', ')}\n`;
                        }
                    });
                }
            }
            break;
        default:
            md += '```json\n' + JSON.stringify(data, null, 2) + '\n```\n';
    }

    return md;
}

// ==========================================
// Accordion Panel Functions
// ==========================================

/**
 * Set up accordion panel toggle behavior.
 */
function setupAccordionPanels() {
    const panels = document.querySelectorAll('.accordion-panel');
    panels.forEach(panel => {
        const header = panel.querySelector('.accordion-header');
        if (header) {
            header.addEventListener('click', (e) => {
                // Don't toggle if clicking on a button inside the panel
                if (e.target.closest('button:not(.accordion-header)')) {
                    return;
                }
                toggleAccordionPanel(panel);
            });
        }
    });
}

/**
 * Toggle an accordion panel open/closed.
 */
function toggleAccordionPanel(panel) {
    const isOpen = panel.classList.contains('open');

    // Close all panels
    document.querySelectorAll('.accordion-panel').forEach(p => {
        p.classList.remove('open');
    });

    // Open clicked panel if it was closed
    if (!isOpen) {
        panel.classList.add('open');
    }
}

/**
 * Update accordion summary text based on current settings.
 */
function updateAccordionSummaries() {
    // Model & Language summary
    const modelSummary = document.getElementById('model-summary');
    if (modelSummary && elements.modelSelect) {
        const modelText = elements.modelSelect.options[elements.modelSelect.selectedIndex]?.text.split(' ')[0] || 'Base';
        // Get language text from the searchable dropdown
        const langText = getSelectedLanguageName() || 'Auto-detect';
        modelSummary.textContent = `${modelText}, ${langText}`;
    }

    // Enhancements summary
    const enhancementsSummary = document.getElementById('enhancements-summary');
    if (enhancementsSummary) {
        const active = [];
        if (elements.enableSpeakers?.checked) active.push('Speakers');
        if (elements.useVocabulary?.checked) active.push('Vocabulary');
        enhancementsSummary.textContent = active.length > 0 ? active.join(', ') : 'None active';
    }

    // Output summary
    const outputSummary = document.getElementById('output-summary');
    if (outputSummary && elements.formatSelect) {
        const formatText = elements.formatSelect.options[elements.formatSelect.selectedIndex]?.text.split(' ')[0] || 'JSON';
        outputSummary.textContent = formatText;
    }

    // Update active features display
    updateActiveFeaturesDisplay();
}

/**
 * Update the active features chip display.
 */
function updateActiveFeaturesDisplay() {
    const container = document.getElementById('active-features');
    if (!container) return;

    const chips = [];

    // Check if using non-default model
    if (elements.modelSelect?.value && elements.modelSelect.value !== 'base') {
        const modelName = elements.modelSelect.options[elements.modelSelect.selectedIndex]?.text.split(' ')[0];
        chips.push(`<span class="feature-chip model"><span class="chip-icon">&#9881;</span> ${modelName}</span>`);
    }

    // Check if language is set (not auto-detect)
    if (AppState.settings.language) {
        const langName = getSelectedLanguageName();
        if (langName && langName !== 'Auto-detect') {
            chips.push(`<span class="feature-chip language"><span class="chip-icon">&#127760;</span> ${langName}</span>`);
        }
    }

    // Check speaker detection
    if (elements.enableSpeakers?.checked) {
        chips.push(`<span class="feature-chip speakers"><span class="chip-icon">&#128101;</span> Speaker Detection</span>`);
    }

    // Check vocabulary
    if (elements.useVocabulary?.checked) {
        chips.push(`<span class="feature-chip vocabulary"><span class="chip-icon">&#128218;</span> Custom Vocabulary</span>`);
    }

    if (chips.length > 0) {
        container.innerHTML = chips.join('');
        container.hidden = false;
    } else {
        container.hidden = true;
    }
}

// ==========================================
// Quick Preset Functions
// ==========================================

/**
 * Set up quick preset button handlers.
 */
function setupPresetButtons() {
    const presetBtns = document.querySelectorAll('.preset-btn');
    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            applyPreset(btn.dataset.preset);

            // Update active state
            presetBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
}

/**
 * Apply a quick preset configuration.
 */
function applyPreset(preset) {
    switch (preset) {
        case 'fast':
            if (elements.modelSelect) elements.modelSelect.value = 'tiny';
            selectLanguage('');  // Auto-detect
            if (elements.enableSpeakers) elements.enableSpeakers.checked = false;
            if (elements.useVocabulary) elements.useVocabulary.checked = false;
            break;

        case 'balanced':
            if (elements.modelSelect) elements.modelSelect.value = 'base';
            selectLanguage('');  // Auto-detect
            if (elements.enableSpeakers) elements.enableSpeakers.checked = false;
            if (elements.useVocabulary) elements.useVocabulary.checked = false;
            break;

        case 'accurate':
            if (elements.modelSelect) elements.modelSelect.value = 'large';
            selectLanguage('');  // Auto-detect
            if (elements.enableSpeakers) elements.enableSpeakers.checked = true;
            if (elements.useVocabulary) elements.useVocabulary.checked = false;
            break;
    }

    // Update AppState
    AppState.settings.model = elements.modelSelect?.value || 'base';
    AppState.settings.enableSpeakers = elements.enableSpeakers?.checked || false;
    AppState.settings.useVocabulary = elements.useVocabulary?.checked || false;

    // Save settings
    saveSettings();

    // Update summaries
    updateAccordionSummaries();
}

/**
 * Update the speaker legend with detected speakers.
 */
function updateSpeakerLegend(speakers) {
    if (!elements.speakerLegend || !elements.legendItems) return;

    if (!speakers || speakers.length === 0) {
        elements.speakerLegend.hidden = true;
        return;
    }

    // Build legend items
    const items = speakers.map((speaker, idx) => {
        const speakerClass = `speaker-${idx % 6}`;
        const displayName = AppState.speakerNames[speaker] || speaker;
        return `<span class="legend-item">
            <span class="legend-dot ${speakerClass}"></span>
            <span>${displayName}</span>
        </span>`;
    }).join('');

    elements.legendItems.innerHTML = items;
    elements.speakerLegend.hidden = false;
}

/**
 * Check speaker detection availability and update UI.
 */
async function checkSpeakerDetectionStatus() {
    const statusEl = document.getElementById('speaker-status');
    if (!statusEl) return;

    try {
        const response = await fetch('/api/settings/status');
        if (response.ok) {
            const status = await response.json();
            if (status.speaker_detection?.available) {
                statusEl.textContent = 'Available';
                statusEl.className = 'enhancement-status available';
            } else {
                statusEl.textContent = 'Not installed';
                statusEl.className = 'enhancement-status unavailable';
                statusEl.title = status.speaker_detection?.error || 'pyannote.audio not installed';
            }
        }
    } catch (e) {
        console.warn('Failed to check speaker detection status:', e);
    }
}

// ============================================================================
// Advanced Settings Functions
// ============================================================================

/**
 * Load current server settings and apply to UI.
 */
async function loadServerSettings() {
    try {
        const response = await fetch('/api/settings/transcription');
        if (response.ok) {
            const settings = await response.json();
            if (elements.maxFileSize && settings.max_memory_mb) {
                elements.maxFileSize.value = settings.max_memory_mb;
                updateAdvancedSummary();
            }
        }
    } catch (e) {
        console.warn('Failed to load server settings:', e);
    }
}

/**
 * Save advanced settings to server.
 */
async function saveAdvancedSettings() {
    const btn = elements.saveAdvancedSettings;
    const status = elements.settingsStatus;

    if (!elements.maxFileSize) return;

    const maxFileSize = parseInt(elements.maxFileSize.value, 10);
    if (isNaN(maxFileSize) || maxFileSize < 100 || maxFileSize > 10000) {
        showSettingsStatus('Invalid value (100-10000 MB)', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Saving...';
    status.textContent = '';
    status.className = 'settings-status';

    try {
        const formData = new FormData();
        formData.append('max_file_size_mb', maxFileSize);

        const response = await fetch('/api/settings/transcription', {
            method: 'PUT',
            body: formData
        });

        if (response.ok) {
            showSettingsStatus('Saved!', 'success');
            updateAdvancedSummary();
        } else {
            const error = await response.json();
            showSettingsStatus(error.detail || 'Failed to save', 'error');
        }
    } catch (e) {
        console.error('Failed to save settings:', e);
        showSettingsStatus('Failed to save', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Settings';
    }
}

/**
 * Show status message for settings.
 * @param {string} message - Status message
 * @param {string} type - 'success' or 'error'
 */
function showSettingsStatus(message, type) {
    const status = elements.settingsStatus;
    if (!status) return;

    status.textContent = message;
    status.className = `settings-status ${type}`;

    // Clear after 3 seconds
    setTimeout(() => {
        status.textContent = '';
        status.className = 'settings-status';
    }, 3000);
}

/**
 * Update advanced settings accordion summary.
 */
function updateAdvancedSummary() {
    if (elements.advancedSummary && elements.maxFileSize) {
        elements.advancedSummary.textContent = `Max: ${elements.maxFileSize.value}MB`;
    }
}

// ============================================================================
// Screen Recording Mode Functions
// ============================================================================

/**
 * Set up screen recording mode event listeners.
 */
function setupScreenRecordingEvents() {
    // Recording mode buttons
    if (elements.recordingModeBtns) {
        elements.recordingModeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                switchRecordingMode(btn.dataset.recordingMode);
            });
        });
    }

    // Banner dismiss button
    if (elements.bannerDismiss) {
        elements.bannerDismiss.addEventListener('click', () => {
            if (elements.platformBanner) {
                elements.platformBanner.hidden = true;
            }
        });
    }

    // Save video checkbox
    if (elements.saveVideoCheckbox) {
        elements.saveVideoCheckbox.addEventListener('change', (e) => {
            // Show/hide audio source options based on checkbox state
            if (elements.videoAudioOptions) {
                elements.videoAudioOptions.hidden = !e.target.checked;
            }
            if (typeof setSaveVideoEnabled === 'function') {
                setSaveVideoEnabled(e.target.checked);
            }
        });
    }

    // Video audio source selection
    if (elements.videoAudioRadios) {
        elements.videoAudioRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (typeof setVideoAudioSource === 'function') {
                    setVideoAudioSource(e.target.value);
                }
            });
        });
    }
}

/**
 * Switch between microphone-only and screen+mic recording modes.
 * @param {string} mode - 'mic' or 'screen'
 */
function switchRecordingMode(mode) {
    // Update button states
    if (elements.recordingModeBtns) {
        elements.recordingModeBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.recordingMode === mode);
        });
    }

    // Set the mode in recorder.js
    if (typeof setRecordingMode === 'function') {
        setRecordingMode(mode);
    }

    // Show/hide screen mode specific UI elements
    const isScreenMode = mode === 'screen';

    // Show/hide save video toggle
    if (elements.saveVideoToggle) {
        elements.saveVideoToggle.hidden = !isScreenMode;
    }

    // Show/hide platform capability banner for screen mode
    if (isScreenMode) {
        showPlatformBanner();
    } else {
        if (elements.platformBanner) {
            elements.platformBanner.hidden = true;
        }
    }

    // Update hint text
    if (elements.recordHint) {
        if (isScreenMode) {
            elements.recordHint.textContent = 'Click to start recording your screen and microphone';
        } else {
            elements.recordHint.textContent = 'Click to start recording from your microphone';
        }
    }
}

/**
 * Show the platform capability banner with appropriate message.
 */
function showPlatformBanner() {
    if (!elements.platformBanner || !elements.platformBannerText) return;

    // Get platform capabilities from recorder.js
    let caps = null;
    if (typeof getPlatformCapabilities === 'function') {
        caps = getPlatformCapabilities();
    }

    if (!caps) return;

    // Set banner text and style
    elements.platformBannerText.textContent = caps.message;

    // Remove existing type classes
    elements.platformBanner.classList.remove('info', 'warning', 'error');

    // Add appropriate type class
    elements.platformBanner.classList.add(caps.messageType);

    // Show the banner
    elements.platformBanner.hidden = false;
}

// ==========================================
// Searchable Language Dropdown Functions
// ==========================================

/**
 * Initialize the searchable language dropdown.
 */
function initLanguageDropdown() {
    if (!elements.languageOptions || !elements.languageSelectTrigger) return;

    // Populate the options
    renderLanguageOptions(WHISPER_LANGUAGES);

    // Set up event listeners
    elements.languageSelectTrigger.addEventListener('click', toggleLanguageDropdown);

    // Search input handling
    if (elements.languageSearch) {
        elements.languageSearch.addEventListener('input', (e) => {
            filterLanguages(e.target.value);
        });

        // Keyboard navigation
        elements.languageSearch.addEventListener('keydown', handleLanguageDropdownKeydown);
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (elements.languageSelectContainer && !elements.languageSelectContainer.contains(e.target)) {
            closeLanguageDropdown();
        }
    });

    // Set initial selection based on AppState
    if (AppState.settings.language) {
        const lang = WHISPER_LANGUAGES.find(l => l.code === AppState.settings.language);
        if (lang && elements.languageSelectedText) {
            elements.languageSelectedText.textContent = lang.name;
        }
    }
}

/**
 * Render the language options list.
 */
function renderLanguageOptions(languages) {
    if (!elements.languageOptions) return;

    if (languages.length === 0) {
        elements.languageOptions.innerHTML = '<div class="no-results">No languages found</div>';
        return;
    }

    const html = languages.map((lang, index) => {
        const isSelected = AppState.settings.language === lang.code;
        const isHighlighted = index === languageDropdownHighlightIndex;
        return `
            <div class="option-item${isSelected ? ' selected' : ''}${isHighlighted ? ' highlighted' : ''}"
                 data-code="${lang.code}" data-index="${index}">
                <span class="lang-name">${lang.name}</span>
                ${lang.code ? `<span class="lang-code">${lang.code}</span>` : ''}
            </div>
        `;
    }).join('');

    elements.languageOptions.innerHTML = html;

    // Add click listeners to options
    elements.languageOptions.querySelectorAll('.option-item').forEach(item => {
        item.addEventListener('click', () => {
            selectLanguage(item.dataset.code);
        });
    });
}

/**
 * Filter languages based on search query.
 */
function filterLanguages(query) {
    const normalizedQuery = query.toLowerCase().trim();

    if (!normalizedQuery) {
        renderLanguageOptions(WHISPER_LANGUAGES);
        languageDropdownHighlightIndex = -1;
        return;
    }

    const filtered = WHISPER_LANGUAGES.filter(lang => {
        return lang.name.toLowerCase().includes(normalizedQuery) ||
               lang.code.toLowerCase().includes(normalizedQuery);
    });

    languageDropdownHighlightIndex = filtered.length > 0 ? 0 : -1;
    renderLanguageOptions(filtered);
}

/**
 * Select a language and close the dropdown.
 */
function selectLanguage(code) {
    AppState.settings.language = code;

    // Update the trigger text
    const lang = WHISPER_LANGUAGES.find(l => l.code === code);
    if (elements.languageSelectedText && lang) {
        elements.languageSelectedText.textContent = lang.name;
    }

    // Close dropdown
    closeLanguageDropdown();

    // Update summaries
    updateAccordionSummaries();
}

/**
 * Get the name of the currently selected language.
 */
function getSelectedLanguageName() {
    const lang = WHISPER_LANGUAGES.find(l => l.code === AppState.settings.language);
    return lang ? lang.name : 'Auto-detect';
}

/**
 * Toggle the language dropdown open/closed.
 */
function toggleLanguageDropdown() {
    if (elements.languageDropdown?.hidden) {
        openLanguageDropdown();
    } else {
        closeLanguageDropdown();
    }
}

/**
 * Open the language dropdown.
 */
function openLanguageDropdown() {
    if (!elements.languageDropdown) return;

    elements.languageDropdown.hidden = false;
    elements.languageSelectContainer?.classList.add('open');

    // Focus search input
    if (elements.languageSearch) {
        elements.languageSearch.value = '';
        elements.languageSearch.focus();
    }

    // Reset filter
    renderLanguageOptions(WHISPER_LANGUAGES);
    languageDropdownHighlightIndex = -1;

    // Scroll selected item into view
    const selectedItem = elements.languageOptions?.querySelector('.option-item.selected');
    if (selectedItem) {
        selectedItem.scrollIntoView({ block: 'nearest' });
    }
}

/**
 * Close the language dropdown.
 */
function closeLanguageDropdown() {
    if (!elements.languageDropdown) return;

    elements.languageDropdown.hidden = true;
    elements.languageSelectContainer?.classList.remove('open');
    languageDropdownHighlightIndex = -1;
}

/**
 * Handle keyboard navigation in the language dropdown.
 */
function handleLanguageDropdownKeydown(e) {
    const items = elements.languageOptions?.querySelectorAll('.option-item');
    if (!items || items.length === 0) return;

    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            languageDropdownHighlightIndex = Math.min(languageDropdownHighlightIndex + 1, items.length - 1);
            updateLanguageHighlight(items);
            break;

        case 'ArrowUp':
            e.preventDefault();
            languageDropdownHighlightIndex = Math.max(languageDropdownHighlightIndex - 1, 0);
            updateLanguageHighlight(items);
            break;

        case 'Enter':
            e.preventDefault();
            if (languageDropdownHighlightIndex >= 0 && items[languageDropdownHighlightIndex]) {
                selectLanguage(items[languageDropdownHighlightIndex].dataset.code);
            }
            break;

        case 'Escape':
            e.preventDefault();
            closeLanguageDropdown();
            elements.languageSelectTrigger?.focus();
            break;
    }
}

/**
 * Update the highlighted item in the dropdown.
 */
function updateLanguageHighlight(items) {
    items.forEach((item, index) => {
        item.classList.toggle('highlighted', index === languageDropdownHighlightIndex);
    });

    // Scroll highlighted item into view
    if (languageDropdownHighlightIndex >= 0 && items[languageDropdownHighlightIndex]) {
        items[languageDropdownHighlightIndex].scrollIntoView({ block: 'nearest' });
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initApp);
