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

    // Set up event listeners
    setupEventListeners();

    // Initialize theme
    initTheme();

    // Initialize sub-modules
    initUploader();
    initRecorder();

    console.log('Transcription app initialized');
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
    elements.languageSelect = document.getElementById('language-select');
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
    elements.newTranscriptionBtn = document.getElementById('new-transcription-btn');
    elements.errorContainer = document.getElementById('error-container');
    elements.errorMessage = document.getElementById('error-message');
    elements.errorDismiss = document.getElementById('error-dismiss');
    elements.liveTranscript = document.getElementById('live-transcript');
    elements.liveText = document.getElementById('live-text');
    elements.recordingActions = document.getElementById('recording-actions');
    elements.downloadAudioBtn = document.getElementById('download-audio-btn');
    elements.newRecordingBtn = document.getElementById('new-recording-btn');

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
    });

    elements.languageSelect.addEventListener('change', (e) => {
        AppState.settings.language = e.target.value;
    });

    elements.formatSelect.addEventListener('change', (e) => {
        AppState.settings.outputFormat = e.target.value;
    });

    elements.enableSpeakers.addEventListener('change', (e) => {
        AppState.settings.enableSpeakers = e.target.checked;
    });

    elements.showTimestamps.addEventListener('change', (e) => {
        AppState.settings.showTimestamps = e.target.checked;
    });

    elements.showConfidence.addEventListener('change', (e) => {
        AppState.settings.showConfidence = e.target.checked;
    });

    // Result actions
    elements.copyBtn.addEventListener('click', copyTranscript);
    elements.downloadBtn.addEventListener('click', downloadTranscript);
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
    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (elements.analyzeMenu && !elements.analyzeMenu.hidden) {
            if (!elements.analyzeBtn.contains(e.target) && !elements.analyzeMenu.contains(e.target)) {
                hideAnalyzeMenu();
            }
        }
    });
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
    AppState.result = null;
}

/**
 * Show error message.
 */
function showError(message) {
    elements.errorMessage.textContent = message;
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
        formData.append('from_code', fromLang);
        formData.append('to_code', toLang);

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
        cleanupModalElements.providerStatus.textContent = 'No providers available';
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
        cleanupModalElements.providerStatus.textContent = 'No providers configured';
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

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initApp);
