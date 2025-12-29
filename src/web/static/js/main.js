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
    },
    result: null,
};

// DOM Elements
const elements = {};

/**
 * Initialize the application.
 */
function initApp() {
    // Cache DOM elements
    cacheElements();

    // Set up event listeners
    setupEventListeners();

    // Initialize sub-modules
    initUploader();
    initRecorder();

    console.log('Transcription app initialized');
}

/**
 * Cache frequently used DOM elements.
 */
function cacheElements() {
    elements.modeBtns = document.querySelectorAll('.mode-btn');
    elements.uploadMode = document.getElementById('upload-mode');
    elements.recordMode = document.getElementById('record-mode');
    elements.modelSelect = document.getElementById('model-select');
    elements.languageSelect = document.getElementById('language-select');
    elements.formatSelect = document.getElementById('format-select');
    elements.enableSpeakers = document.getElementById('enable-speakers');
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
}

/**
 * Set up event listeners.
 */
function setupEventListeners() {
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
}

/**
 * Switch between upload and record modes.
 */
function switchMode(mode) {
    AppState.mode = mode;

    // Update button states
    elements.modeBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Show/hide mode content
    elements.uploadMode.classList.toggle('active', mode === 'upload');
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

    // Display transcript
    elements.transcriptText.textContent = result.text || '';

    // Display metadata
    elements.resultLanguage.textContent = `Language: ${result.language || 'Unknown'}`;
    elements.resultConfidence.textContent = `Confidence: ${Math.round((result.confidence || 0) * 100)}%`;
    elements.resultTime.textContent = `Time: ${(result.processing_time || 0).toFixed(1)}s`;

    // Show container
    elements.resultsContainer.hidden = false;
    hideProgress();
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
 * Download transcript.
 */
function downloadTranscript() {
    if (!AppState.result?.text) return;

    const format = AppState.settings.outputFormat;
    let content = AppState.result.text;
    let mimeType = 'text/plain';
    let extension = 'txt';

    if (format === 'json') {
        content = JSON.stringify(AppState.result, null, 2);
        mimeType = 'application/json';
        extension = 'json';
    } else if (format === 'srt' || format === 'vtt') {
        // For SRT/VTT, we'd need segment data
        // For now, just download as text
        extension = format;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript.${extension}`;
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

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initApp);
