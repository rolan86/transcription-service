/**
 * Audio recorder for real-time transcription.
 * Uses Web Audio API for PCM capture and MediaRecorder for saving.
 * Supports long recordings (1+ hours) with server-side chunk persistence.
 * Supports screen + mic recording for capturing video calls.
 */

let recorderElements = {};
let mediaRecorder = null;
let audioContext = null;
let analyser = null;
let scriptProcessor = null;
let mediaStream = null;
let recordingStartTime = null;
let timerInterval = null;
let wsClient = null;

// For saving audio (browser-side buffer)
let recordedChunks = [];
let recordedAudioBlob = null;

// For long recording support
let pcmChunks = [];  // PCM audio chunks for flushing to server
let flushInterval = null;
let sessionId = null;
let lastFlushTime = 0;
const FLUSH_INTERVAL_MS = 30000;  // Flush every 30 seconds
const MAX_BROWSER_CHUNKS = 500;   // Max chunks to keep in browser memory

// ============================================================================
// Screen Recording Support
// ============================================================================

// Recording mode: 'mic' for microphone only, 'screen' for screen + mic
let recordingMode = 'mic';

// Screen capture streams and tracks
let screenStream = null;
let screenVideoTrack = null;
let screenAudioTrack = null;
let micStream = null;

// Video recording (optional)
let videoRecorder = null;
let videoChunks = [];
let recordedVideoBlob = null;
let saveVideoEnabled = false;
let videoAudioSource = 'mixed';  // 'screen' | 'mixed' - whether to include mic audio in video

// Platform capabilities
let platformCapabilities = null;

// Pause/Resume state
let isPaused = false;
let pauseStartTime = null;
let totalPausedTime = 0;

// Chapters state
let chapters = [];
let chapterStartTime = 0;  // Start time of current chapter (elapsed ms)

// Session continuation state
let lastSessionId = null;
let priorDuration = 0;  // Duration from previous session continuation (ms)

/**
 * Initialize the recorder.
 */
function initRecorder() {
    recorderElements.recordBtn = document.getElementById('record-btn');
    recorderElements.recordIcon = recorderElements.recordBtn.querySelector('.record-icon');
    recorderElements.recordText = recorderElements.recordBtn.querySelector('.record-text');
    recorderElements.recordTimer = document.getElementById('record-timer');
    recorderElements.audioLevel = document.getElementById('audio-level');
    recorderElements.levelBar = recorderElements.audioLevel.querySelector('.level-bar');
    recorderElements.deferredWarning = document.getElementById('deferred-transcription-warning');
    recorderElements.pauseBtn = document.getElementById('pause-btn');
    recorderElements.chapterBtn = document.getElementById('chapter-btn');
    recorderElements.chapterList = document.getElementById('chapter-list');
    recorderElements.continueBtn = document.getElementById('continue-recording-btn');

    setupRecorderEvents();
}

/**
 * Set up recorder event listeners.
 */
function setupRecorderEvents() {
    recorderElements.recordBtn.addEventListener('click', toggleRecording);
    if (recorderElements.pauseBtn) {
        recorderElements.pauseBtn.addEventListener('click', togglePause);
    }
    if (recorderElements.chapterBtn) {
        recorderElements.chapterBtn.addEventListener('click', addChapter);
    }
    if (recorderElements.continueBtn) {
        recorderElements.continueBtn.addEventListener('click', continueRecording);
    }
}

/**
 * Show deferred transcription warning banner.
 * @param {string} modelStatus - Current model status
 */
function showDeferredTranscriptionWarning(modelStatus) {
    if (recorderElements.deferredWarning) {
        recorderElements.deferredWarning.hidden = false;
        const statusText = recorderElements.deferredWarning.querySelector('.warning-status');
        if (statusText) {
            statusText.textContent = modelStatus === 'loading' ?
                'Model loading...' : 'Model not ready';
        }
    }
    console.warn('Deferred transcription: Model status is', modelStatus);
}

/**
 * Hide deferred transcription warning banner.
 */
function hideDeferredTranscriptionWarning() {
    if (recorderElements.deferredWarning) {
        recorderElements.deferredWarning.hidden = true;
    }
}

/**
 * Toggle pause/resume state.
 */
function togglePause() {
    if (isPaused) {
        resumeRecording();
    } else {
        pauseRecording();
    }
}

/**
 * Pause the recording.
 * Stops capturing audio but keeps the session active.
 */
function pauseRecording() {
    if (!mediaRecorder || mediaRecorder.state !== 'recording' || isPaused) {
        return;
    }

    isPaused = true;
    pauseStartTime = Date.now();

    // Disconnect script processor to stop sending audio
    if (scriptProcessor) {
        scriptProcessor.onaudioprocess = null;
    }

    // Pause MediaRecorder
    if (mediaRecorder.state === 'recording') {
        mediaRecorder.pause();
    }

    // Send pause message to server
    if (wsClient && wsClient.isConnected) {
        wsClient.send({ type: 'pause' });
    }

    // Pause timer
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    // Update UI
    updatePauseUI(true);

    console.log('Recording paused');
}

/**
 * Resume the recording.
 */
function resumeRecording() {
    if (!mediaRecorder || !isPaused) {
        return;
    }

    isPaused = false;
    if (pauseStartTime) {
        totalPausedTime += Date.now() - pauseStartTime;
        pauseStartTime = null;
    }

    // Reconnect script processor
    if (scriptProcessor) {
        scriptProcessor.onaudioprocess = (event) => {
            if (wsClient && wsClient.isConnected) {
                const inputData = event.inputBuffer.getChannelData(0);
                const pcmData = float32ToInt16(inputData);
                pcmChunks.push(new Int16Array(pcmData));
                const base64 = arrayBufferToBase64(pcmData.buffer);
                wsClient.send({ type: 'audio', data: base64 });
            }
        };
    }

    // Resume MediaRecorder
    if (mediaRecorder.state === 'paused') {
        mediaRecorder.resume();
    }

    // Send resume message to server
    if (wsClient && wsClient.isConnected) {
        wsClient.send({ type: 'resume' });
    }

    // Resume timer
    startTimer();

    // Update UI
    updatePauseUI(false);

    console.log('Recording resumed');
}

/**
 * Update UI for pause/resume state.
 * @param {boolean} paused - Whether recording is paused
 */
function updatePauseUI(paused) {
    if (recorderElements.pauseBtn) {
        const pauseText = recorderElements.pauseBtn.querySelector('.pause-text');
        if (pauseText) {
            pauseText.textContent = paused ? 'Resume' : 'Pause';
        }
        recorderElements.pauseBtn.classList.toggle('paused', paused);
    }

    // Also update record button to show paused state
    recorderElements.recordBtn.classList.toggle('paused', paused);
}

/**
 * Add a chapter marker at current position.
 */
function addChapter() {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        return;
    }

    // Calculate elapsed time (excluding paused time)
    const elapsed = Date.now() - recordingStartTime - totalPausedTime;

    // Close previous chapter if exists
    if (chapters.length > 0) {
        chapters[chapters.length - 1].endTime = elapsed;
    }

    // Create new chapter
    const chapterIndex = chapters.length + 1;
    const chapter = {
        index: chapterIndex,
        title: `Chapter ${chapterIndex}`,
        startTime: elapsed,
        endTime: null,  // Will be set when next chapter starts or recording ends
    };

    chapters.push(chapter);

    // Send chapter message to server
    if (wsClient && wsClient.isConnected) {
        wsClient.send({ type: 'chapter', chapter: chapter });
    }

    // Update UI
    updateChapterListUI();

    console.log('Chapter added:', chapter);
}

/**
 * Update chapter list UI.
 */
function updateChapterListUI() {
    if (!recorderElements.chapterList) return;

    if (chapters.length === 0) {
        recorderElements.chapterList.hidden = true;
        return;
    }

    recorderElements.chapterList.hidden = false;

    const listHtml = chapters.map(ch => {
        const startFormatted = formatTime(ch.startTime);
        const endFormatted = ch.endTime ? formatTime(ch.endTime) : 'now';
        return `
            <div class="chapter-item" data-index="${ch.index}">
                <span class="chapter-title">${ch.title}</span>
                <span class="chapter-time">${startFormatted} - ${endFormatted}</span>
            </div>
        `;
    }).join('');

    recorderElements.chapterList.innerHTML = listHtml;
}

/**
 * Format milliseconds as mm:ss.
 * @param {number} ms - Milliseconds
 * @returns {string} Formatted time
 */
function formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Reset chapter state.
 */
function resetChapters() {
    chapters = [];
    chapterStartTime = 0;
    if (recorderElements.chapterList) {
        recorderElements.chapterList.innerHTML = '';
        recorderElements.chapterList.hidden = true;
    }
}

/**
 * Continue a previous recording session.
 * Appends new audio/transcript to the existing session.
 */
async function continueRecording() {
    if (!lastSessionId) {
        console.error('No session to continue');
        return;
    }

    // Hide continue button
    if (recorderElements.continueBtn) {
        recorderElements.continueBtn.hidden = true;
    }

    // Get current settings
    const modelSelect = document.getElementById('transcription-model');
    const languageSelect = document.getElementById('transcription-language');
    const model = modelSelect?.value || 'base';
    const language = languageSelect?.value || null;

    try {
        // Reset some state but keep prior duration
        recordedChunks = [];
        recordedAudioBlob = null;
        pcmChunks = [];
        lastFlushTime = Date.now();
        videoChunks = [];
        recordedVideoBlob = null;
        isPaused = false;
        pauseStartTime = null;
        totalPausedTime = 0;
        // Don't reset chapters - we'll restore them from the server

        // Request microphone access
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            }
        });

        // Set up audio context for PCM capture
        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);

        // Analyser for level visualization
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        // Script processor for raw PCM data
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        // Connect to WebSocket with continue message
        wsClient = new TranscriptionWebSocket();

        // Handle continue_ready message
        wsClient.onMessage = (message) => {
            if (message.type === 'continue_ready') {
                // Restore prior state
                priorDuration = (message.prior_duration || 0) * 1000; // Convert to ms
                sessionId = message.session_id;

                // Restore chapters from server
                if (message.prior_chapters && message.prior_chapters.length > 0) {
                    chapters = message.prior_chapters;
                    updateChapterListUI();
                }

                // Update transcript with prior text
                if (message.prior_transcript) {
                    const transcript = document.getElementById('live-transcript');
                    if (transcript) {
                        transcript.textContent = message.prior_transcript + '\n\n[Continuing...]\n';
                    }
                }

                // Connect script processor
                scriptProcessor.onaudioprocess = (event) => {
                    if (wsClient && wsClient.isConnected) {
                        const inputData = event.inputBuffer.getChannelData(0);
                        const pcmData = float32ToInt16(inputData);
                        pcmChunks.push(new Int16Array(pcmData));
                        const base64 = arrayBufferToBase64(pcmData.buffer);
                        wsClient.send({ type: 'audio', data: base64 });
                    }
                };

                source.connect(scriptProcessor);
                scriptProcessor.connect(audioContext.destination);

                // Start recording
                recordingStartTime = Date.now() - priorDuration;
                startTimer();
                startFlushInterval();

                // Update UI
                recorderElements.recordBtn.classList.add('recording');
                recorderElements.recordText.textContent = 'Stop';
                if (recorderElements.pauseBtn) {
                    recorderElements.pauseBtn.hidden = false;
                }
                if (recorderElements.chapterBtn) {
                    recorderElements.chapterBtn.hidden = false;
                }
                showLiveTranscript();
                visualizeAudioLevel();
            } else if (message.type === 'transcript') {
                updateTranscript(message);
            } else if (message.type === 'complete') {
                handleComplete(message);
            } else if (message.type === 'error') {
                showError(message.error);
            }
        };

        // Connect and send continue message
        await wsClient.connect();
        wsClient.send({
            type: 'continue',
            session_id: lastSessionId,
            model: model,
            language: language,
            sample_rate: 16000,
        });

        // Set up MediaRecorder for audio blob
        mediaRecorder = new MediaRecorder(mediaStream);
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };
        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: 'audio/webm' });
            recordedAudioBlob = blob;
        };
        mediaRecorder.start(1000);

    } catch (error) {
        console.error('Error continuing recording:', error);
        showError('Failed to continue recording: ' + error.message);
        // Show the continue button again on error
        if (recorderElements.continueBtn) {
            recorderElements.continueBtn.hidden = false;
        }
    }
}

/**
 * Show the continue recording button if session can be continued.
 * @param {string} sessionId - The session ID to continue
 */
function showContinueButton(sessionId) {
    lastSessionId = sessionId;
    if (recorderElements.continueBtn && sessionId) {
        recorderElements.continueBtn.hidden = false;
    }
}

/**
 * Hide the continue recording button.
 */
function hideContinueButton() {
    lastSessionId = null;
    priorDuration = 0;
    if (recorderElements.continueBtn) {
        recorderElements.continueBtn.hidden = true;
    }
}

/**
 * Toggle recording on/off.
 */
async function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        await startRecording();
    }
}

/**
 * Start recording audio.
 */
async function startRecording() {
    // Check recording mode and delegate to appropriate function
    if (recordingMode === 'screen') {
        return await startScreenModeRecording();
    }

    // Microphone-only mode (original implementation)
    try {
        // Reset state
        recordedChunks = [];
        recordedAudioBlob = null;
        pcmChunks = [];
        sessionId = null;
        lastFlushTime = Date.now();
        videoChunks = [];
        recordedVideoBlob = null;
        // Reset pause state
        isPaused = false;
        pauseStartTime = null;
        totalPausedTime = 0;

        // Reset chapters
        resetChapters();

        // Request microphone access
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            }
        });

        // Set up audio context for PCM capture
        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);

        // Analyser for level visualization
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        // Script processor for raw PCM data (for real-time transcription)
        // Note: ScriptProcessorNode is deprecated but AudioWorklet requires HTTPS
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        // Connect to WebSocket
        wsClient = new TranscriptionWebSocket();

        // Handle session_id and model status from ready message
        const originalOnReady = wsClient.onReady;
        wsClient.onReady = (message) => {
            if (message.session_id) {
                sessionId = message.session_id;
                console.log('Recording session started:', sessionId);
            }
            // Handle deferred transcription (model not ready)
            if (message.deferred_transcription) {
                showDeferredTranscriptionWarning(message.model_status);
            } else {
                hideDeferredTranscriptionWarning();
            }
            if (originalOnReady) originalOnReady(message);
        };

        await wsClient.connect();

        // Start streaming config with persistence enabled
        wsClient.send({
            type: 'start',
            model: AppState.settings.model,
            language: AppState.settings.language || null,
            sample_rate: 16000,
            enable_persistence: true,
        });

        // Process audio data for streaming
        scriptProcessor.onaudioprocess = (event) => {
            if (wsClient && wsClient.isConnected) {
                const inputData = event.inputBuffer.getChannelData(0);

                // Convert Float32 to Int16 PCM
                const pcmData = float32ToInt16(inputData);

                // Store PCM data for flushing to server
                pcmChunks.push(new Int16Array(pcmData));

                // Convert to base64 and send for real-time transcription
                const base64 = arrayBufferToBase64(pcmData.buffer);
                wsClient.send({
                    type: 'audio',
                    data: base64,
                });
            }
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        // MediaRecorder for saving audio file (WebM format)
        mediaRecorder = new MediaRecorder(mediaStream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            // Create blob from recorded chunks
            recordedAudioBlob = new Blob(recordedChunks, { type: 'audio/webm' });
            console.log('Recording saved, size:', recordedAudioBlob.size);
        };

        // Start recording
        mediaRecorder.start(1000); // Save chunks every second
        recordingStartTime = Date.now();

        // Start periodic flush for long recordings
        startFlushInterval();

        // Update UI
        recorderElements.recordBtn.classList.add('recording');
        recorderElements.recordText.textContent = 'Stop';
        if (recorderElements.pauseBtn) {
            recorderElements.pauseBtn.hidden = false;
        }
        if (recorderElements.chapterBtn) {
            recorderElements.chapterBtn.hidden = false;
        }
        showLiveTranscript();

        // Start timer
        startTimer();

        // Start audio level visualization
        visualizeAudioLevel();

    } catch (error) {
        console.error('Error starting recording:', error);
        showError('Failed to access microphone: ' + error.message);
    }
}

/**
 * Stop recording audio.
 */
async function stopRecording() {
    // Stop flush interval
    stopFlushInterval();

    // Flush any remaining chunks before stopping
    if (pcmChunks.length > 0 && wsClient && wsClient.isConnected && sessionId) {
        await flushChunksToServer();
    }

    // Stop script processor
    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }

    // Stop media recorder (this triggers onstop and saves the blob)
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }

    // Stop timer
    stopTimer();

    // Finalize transcription via WebSocket
    if (wsClient) {
        wsClient.send({ type: 'stop' });
    }

    // Stop media stream
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }

    // Clean up screen recording resources if in screen mode
    if (recordingMode === 'screen') {
        cleanupScreenRecording();
    }

    // Clean up audio context
    if (audioContext) {
        audioContext.close();
        audioContext = null;
        analyser = null;
    }

    // Update UI
    recorderElements.recordBtn.classList.remove('recording');
    recorderElements.recordBtn.classList.remove('paused');
    recorderElements.recordText.textContent = 'Start Recording';
    recorderElements.levelBar.style.width = '0%';
    if (recorderElements.pauseBtn) {
        recorderElements.pauseBtn.hidden = true;
        recorderElements.pauseBtn.classList.remove('paused');
    }
    if (recorderElements.chapterBtn) {
        recorderElements.chapterBtn.hidden = true;
    }

    // Close final chapter if exists
    if (chapters.length > 0) {
        const elapsed = Date.now() - recordingStartTime - totalPausedTime;
        chapters[chapters.length - 1].endTime = elapsed;
    }

    // Reset pause state
    isPaused = false;
    pauseStartTime = null;
    totalPausedTime = 0;

    // Reset long recording state
    pcmChunks = [];
    sessionId = null;

    // Don't close WebSocket here - let it close after receiving 'complete' message
    // The websocket.js handleComplete() will handle cleanup

    mediaRecorder = null;
}

/**
 * Convert Float32Array to Int16Array (PCM format).
 */
function float32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
        // Clamp and convert
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
}

/**
 * Convert ArrayBuffer to base64 string.
 */
function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

// ============================================================================
// Platform Detection & Capabilities
// ============================================================================

/**
 * Detect platform capabilities for screen audio capture.
 */
function detectPlatformCapabilities() {
    const ua = navigator.userAgent;

    // Detect OS
    let os = 'unknown';
    if (ua.includes('Windows')) os = 'windows';
    else if (ua.includes('Mac')) os = 'macos';
    else if (ua.includes('Linux')) os = 'linux';

    // Detect browser
    let browser = 'unknown';
    if (ua.includes('Firefox')) browser = 'firefox';
    else if (ua.includes('Edg/')) browser = 'edge';
    else if (ua.includes('Chrome')) browser = 'chrome';
    else if (ua.includes('Safari')) browser = 'safari';

    // Determine capabilities
    let systemAudio = false;
    let tabAudio = false;
    let message = '';
    let messageType = 'info'; // 'info', 'warning', 'error'

    if (browser === 'firefox') {
        // Firefox doesn't support audio in getDisplayMedia
        systemAudio = false;
        tabAudio = false;
        messageType = 'warning';
        message = 'Firefox: Screen video works, but only microphone audio will be captured (no screen audio). For full audio capture, use Chrome or Edge.';
    } else if (os === 'windows' && (browser === 'chrome' || browser === 'edge')) {
        // Windows Chrome/Edge: Full system audio support
        systemAudio = true;
        tabAudio = true;
        messageType = 'info';
        message = 'Full system audio capture available.';
    } else if (os === 'macos') {
        // macOS: Only tab audio without additional software
        systemAudio = false;
        tabAudio = true;
        messageType = 'warning';
        message = 'macOS: Only browser tab audio will be captured. For full system audio, install BlackHole or similar audio routing software.';
    } else if (os === 'linux') {
        // Linux: Only tab audio without additional setup
        systemAudio = false;
        tabAudio = true;
        messageType = 'warning';
        message = 'Linux: Only browser tab audio will be captured. For full system audio, configure PulseAudio loopback.';
    } else {
        // Unknown platform
        tabAudio = true;
        messageType = 'info';
        message = 'Screen audio capture may be limited on this platform.';
    }

    platformCapabilities = {
        os,
        browser,
        systemAudio,
        tabAudio,
        message,
        messageType,
        supportsScreenAudio: browser !== 'firefox',
    };

    return platformCapabilities;
}

/**
 * Get the current platform capabilities.
 */
function getPlatformCapabilities() {
    if (!platformCapabilities) {
        detectPlatformCapabilities();
    }
    return platformCapabilities;
}

// ============================================================================
// Audio Mixing (Screen + Mic)
// ============================================================================

/**
 * Create an audio mixer that combines screen audio and microphone audio.
 * Uses gain node summing to create a proper mono mix.
 *
 * @param {MediaStreamTrack|null} screenAudioTrack - Audio track from screen capture
 * @param {MediaStreamTrack} micAudioTrack - Audio track from microphone
 * @returns {Object} Object containing the AudioContext and mixed output stream
 */
function createAudioMixer(screenAudioTrackInput, micAudioTrackInput) {
    // Create audio context at 16kHz for Whisper compatibility
    const ctx = new AudioContext({ sampleRate: 16000 });

    // Create a single gain node as the mixer (summing node)
    // Connecting multiple sources to one gain node automatically sums them into mono
    const mixerGain = ctx.createGain();
    mixerGain.gain.value = 0.8;  // Slight reduction to prevent clipping when mixing

    // Create destination for mixed output
    const destination = ctx.createMediaStreamDestination();

    // Create individual gain nodes for volume control
    const screenGain = ctx.createGain();
    const micGain = ctx.createGain();
    screenGain.gain.value = 1.0;
    micGain.gain.value = 1.0;

    // Connect screen audio if available
    if (screenAudioTrackInput) {
        const screenSource = ctx.createMediaStreamSource(
            new MediaStream([screenAudioTrackInput])
        );
        screenSource.connect(screenGain);
        screenGain.connect(mixerGain);  // Both go to SAME mixer node
        console.log('Screen audio connected to mixer');
    }

    // Connect microphone audio
    const micSource = ctx.createMediaStreamSource(
        new MediaStream([micAudioTrackInput])
    );
    micSource.connect(micGain);
    micGain.connect(mixerGain);  // Both go to SAME mixer node (sums signals)
    console.log('Microphone audio connected to mixer');

    // Connect mixer to destination
    mixerGain.connect(destination);

    return {
        context: ctx,
        stream: destination.stream,
        screenGain,
        micGain,
        mixerGain,
    };
}

// ============================================================================
// Screen Recording Functions
// ============================================================================

/**
 * Set the recording mode.
 * @param {string} mode - 'mic' or 'screen'
 */
function setRecordingMode(mode) {
    if (mode === 'mic' || mode === 'screen') {
        recordingMode = mode;
        console.log('Recording mode set to:', mode);
    }
}

/**
 * Get the current recording mode.
 */
function getRecordingMode() {
    return recordingMode;
}

/**
 * Set whether video saving is enabled.
 */
function setSaveVideoEnabled(enabled) {
    saveVideoEnabled = enabled;
    console.log('Save video enabled:', enabled);
}

/**
 * Check if video saving is enabled.
 */
function isSaveVideoEnabled() {
    return saveVideoEnabled;
}

/**
 * Set the video audio source.
 * @param {string} source - 'screen' or 'mixed'
 */
function setVideoAudioSource(source) {
    if (source === 'screen' || source === 'mixed') {
        videoAudioSource = source;
        console.log('Video audio source set to:', source);
    }
}

/**
 * Get the current video audio source setting.
 */
function getVideoAudioSource() {
    return videoAudioSource;
}

/**
 * Start screen + microphone recording.
 */
async function startScreenModeRecording() {
    try {
        // Reset state
        recordedChunks = [];
        recordedAudioBlob = null;
        pcmChunks = [];
        sessionId = null;
        lastFlushTime = Date.now();
        videoChunks = [];
        recordedVideoBlob = null;
        // Reset pause state
        isPaused = false;
        pauseStartTime = null;
        totalPausedTime = 0;

        // Reset chapters
        resetChapters();

        // Detect platform capabilities
        const caps = getPlatformCapabilities();

        // Request screen share with audio
        const displayMediaOptions = {
            video: {
                cursor: 'always',
            },
            audio: caps.supportsScreenAudio ? {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
            } : false,
        };

        try {
            screenStream = await navigator.mediaDevices.getDisplayMedia(displayMediaOptions);
        } catch (screenErr) {
            if (screenErr.name === 'NotAllowedError') {
                throw new Error('Screen sharing was denied. Please allow screen sharing to continue.');
            }
            throw screenErr;
        }

        // Get tracks from screen stream
        screenVideoTrack = screenStream.getVideoTracks()[0];
        screenAudioTrack = screenStream.getAudioTracks()[0] || null;

        // Handle screen share ending (user clicks browser stop button)
        screenVideoTrack.onended = () => {
            console.log('Screen share ended by user');
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                stopRecording();
            }
        };

        // Show screen preview if element exists
        const previewVideo = document.getElementById('screen-preview-video');
        if (previewVideo) {
            previewVideo.srcObject = screenStream;
            const previewContainer = document.getElementById('screen-preview');
            if (previewContainer) {
                previewContainer.hidden = false;
            }
        }

        // Request microphone access
        micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            }
        });

        const micAudioTrack = micStream.getAudioTracks()[0];

        // Log what we got
        console.log('Screen audio track:', screenAudioTrack ? 'available' : 'not available');
        console.log('Mic audio track:', micAudioTrack ? 'available' : 'not available');

        // Create mixed audio stream
        const mixer = createAudioMixer(screenAudioTrack, micAudioTrack);
        audioContext = mixer.context;

        // Get the mixed audio stream
        const mixedStream = mixer.stream;

        // Use mixed stream as the main media stream
        mediaStream = mixedStream;

        // Set up source from mixed stream
        const source = audioContext.createMediaStreamSource(mixedStream);

        // Analyser for level visualization
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        // Script processor for raw PCM data
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        // Connect to WebSocket
        wsClient = new TranscriptionWebSocket();

        // Handle session_id and model status from ready message
        const originalOnReady = wsClient.onReady;
        wsClient.onReady = (message) => {
            if (message.session_id) {
                sessionId = message.session_id;
                console.log('Recording session started:', sessionId);
            }
            // Handle deferred transcription (model not ready)
            if (message.deferred_transcription) {
                showDeferredTranscriptionWarning(message.model_status);
            } else {
                hideDeferredTranscriptionWarning();
            }
            if (originalOnReady) originalOnReady(message);
        };

        await wsClient.connect();

        // Start streaming config with persistence enabled
        wsClient.send({
            type: 'start',
            model: AppState.settings.model,
            language: AppState.settings.language || null,
            sample_rate: 16000,
            enable_persistence: true,
        });

        // Process audio data for streaming
        scriptProcessor.onaudioprocess = (event) => {
            if (wsClient && wsClient.isConnected) {
                const inputData = event.inputBuffer.getChannelData(0);

                // Convert Float32 to Int16 PCM
                const pcmData = float32ToInt16(inputData);

                // Store PCM data for flushing to server
                pcmChunks.push(new Int16Array(pcmData));

                // Convert to base64 and send for real-time transcription
                const base64 = arrayBufferToBase64(pcmData.buffer);
                wsClient.send({
                    type: 'audio',
                    data: base64,
                });
            }
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        // MediaRecorder for saving mixed audio (WebM format)
        mediaRecorder = new MediaRecorder(mixedStream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            recordedAudioBlob = new Blob(recordedChunks, { type: 'audio/webm' });
            console.log('Recording saved, size:', recordedAudioBlob.size);
        };

        // Start video recording if enabled
        if (saveVideoEnabled && screenVideoTrack) {
            startVideoRecording(screenVideoTrack, screenAudioTrack, mixedStream);
        }

        // Start audio recording
        mediaRecorder.start(1000);
        recordingStartTime = Date.now();

        // Start periodic flush for long recordings
        startFlushInterval();

        // Update UI
        recorderElements.recordBtn.classList.add('recording');
        recorderElements.recordText.textContent = 'Stop';
        if (recorderElements.pauseBtn) {
            recorderElements.pauseBtn.hidden = false;
        }
        if (recorderElements.chapterBtn) {
            recorderElements.chapterBtn.hidden = false;
        }
        showLiveTranscript();

        // Start timer
        startTimer();

        // Start audio level visualization
        visualizeAudioLevel();

    } catch (error) {
        console.error('Error starting screen recording:', error);

        // Clean up any partially acquired streams
        cleanupScreenRecording();

        showError('Failed to start screen recording: ' + error.message);
    }
}

/**
 * Start video recording (optional feature).
 * @param {MediaStreamTrack} videoTrack - The video track to record
 * @param {MediaStreamTrack|null} screenAudioTrackParam - Screen audio track (may be null)
 * @param {MediaStream|null} mixedStream - Mixed audio stream (screen + mic)
 */
function startVideoRecording(videoTrack, screenAudioTrackParam, mixedStream) {
    if (!saveVideoEnabled || !videoTrack) return;

    try {
        // Create stream with video and audio based on user preference
        const tracks = [videoTrack];

        // Choose audio source based on setting
        if (videoAudioSource === 'mixed' && mixedStream) {
            // Use mixed audio (screen + microphone)
            const mixedAudioTrack = mixedStream.getAudioTracks()[0];
            if (mixedAudioTrack) {
                tracks.push(mixedAudioTrack);
                console.log('Video recording: using mixed audio (screen + mic)');
            }
        } else if (screenAudioTrackParam) {
            // Use screen audio only
            tracks.push(screenAudioTrackParam);
            console.log('Video recording: using screen audio only');
        }

        const videoStream = new MediaStream(tracks);

        // Determine best codec
        let mimeType = 'video/webm;codecs=vp9';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'video/webm;codecs=vp8';
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'video/webm';
        }

        videoRecorder = new MediaRecorder(videoStream, { mimeType });
        videoChunks = [];

        videoRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                videoChunks.push(e.data);
            }
        };

        videoRecorder.onstop = () => {
            recordedVideoBlob = new Blob(videoChunks, { type: 'video/webm' });
            console.log('Video recording saved, size:', recordedVideoBlob.size);

            // Show download button if video was recorded
            const downloadVideoBtn = document.getElementById('download-video-btn');
            if (downloadVideoBtn && recordedVideoBlob.size > 0) {
                downloadVideoBtn.hidden = false;
            }
        };

        videoRecorder.start(1000); // Chunk every second
        console.log('Video recording started with codec:', mimeType);

    } catch (error) {
        console.error('Error starting video recording:', error);
        // Continue without video recording
    }
}

/**
 * Stop video recording.
 */
function stopVideoRecording() {
    if (videoRecorder && videoRecorder.state === 'recording') {
        videoRecorder.stop();
        videoRecorder = null;
    }
}

/**
 * Download the recorded video file.
 */
function downloadRecordedVideo() {
    if (!recordedVideoBlob) {
        showError('No video recording available to download');
        return;
    }

    // Generate default filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const defaultName = `screen_recording_${timestamp}`;

    // Show modal to get filename
    showModal('Save Video Recording', defaultName, '.webm', (filename) => {
        performVideoDownload(filename);
    });
}

/**
 * Perform the actual video download.
 */
function performVideoDownload(filename) {
    const url = URL.createObjectURL(recordedVideoBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Check if there's a recorded video available.
 */
function hasRecordedVideo() {
    return recordedVideoBlob !== null && recordedVideoBlob.size > 0;
}

/**
 * Clean up screen recording resources.
 */
function cleanupScreenRecording() {
    // Stop video recording
    stopVideoRecording();

    // Stop screen stream
    if (screenStream) {
        screenStream.getTracks().forEach(track => track.stop());
        screenStream = null;
    }

    // Stop mic stream
    if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        micStream = null;
    }

    // Clear track references
    screenVideoTrack = null;
    screenAudioTrack = null;

    // Hide screen preview
    const previewContainer = document.getElementById('screen-preview');
    if (previewContainer) {
        previewContainer.hidden = true;
    }
    const previewVideo = document.getElementById('screen-preview-video');
    if (previewVideo) {
        previewVideo.srcObject = null;
    }
}

/**
 * Download the recorded audio file with filename prompt.
 */
function downloadRecordedAudio() {
    if (!recordedAudioBlob) {
        showError('No recording available to download');
        return;
    }

    // Generate default filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const defaultName = `recording_${timestamp}`;

    // Show modal to get filename
    showModal('Save Recording', defaultName, '.webm', (filename) => {
        performAudioDownload(filename);
    });
}

/**
 * Perform the actual audio download.
 */
function performAudioDownload(filename) {
    const url = URL.createObjectURL(recordedAudioBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Check if there's a recorded audio available.
 */
function hasRecordedAudio() {
    return recordedAudioBlob !== null;
}

/**
 * Get the recorded audio blob.
 */
function getRecordedAudioBlob() {
    return recordedAudioBlob;
}

/**
 * Start the recording timer.
 * Supports HH:MM:SS format for recordings over 1 hour.
 * Accounts for paused time.
 */
function startTimer() {
    timerInterval = setInterval(() => {
        const elapsed = Date.now() - recordingStartTime - totalPausedTime;
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);

        if (hours > 0) {
            recorderElements.recordTimer.textContent =
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        } else {
            recorderElements.recordTimer.textContent =
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

/**
 * Stop the recording timer.
 */
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

/**
 * Visualize audio input level.
 */
function visualizeAudioLevel() {
    if (!analyser) return;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    function update() {
        if (!analyser) return;

        analyser.getByteFrequencyData(dataArray);

        // Calculate average level
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const percent = Math.min(100, (average / 128) * 100);

        recorderElements.levelBar.style.width = `${percent}%`;

        if (mediaRecorder && mediaRecorder.state === 'recording') {
            requestAnimationFrame(update);
        }
    }

    update();
}

// ============================================================================
// Long Recording Support - Server-side chunk persistence
// ============================================================================

/**
 * Start the periodic flush interval for long recordings.
 */
function startFlushInterval() {
    if (flushInterval) {
        clearInterval(flushInterval);
    }

    flushInterval = setInterval(() => {
        if (pcmChunks.length > 0 && wsClient && wsClient.isConnected && sessionId) {
            flushChunksToServer();
        }
    }, FLUSH_INTERVAL_MS);

    console.log('Long recording support enabled - chunks will flush every', FLUSH_INTERVAL_MS / 1000, 'seconds');
}

/**
 * Stop the flush interval.
 */
function stopFlushInterval() {
    if (flushInterval) {
        clearInterval(flushInterval);
        flushInterval = null;
    }
}

/**
 * Flush accumulated PCM chunks to the server.
 * This prevents browser memory overflow for long recordings.
 */
async function flushChunksToServer() {
    if (!wsClient || !wsClient.isConnected || !sessionId) {
        console.warn('Cannot flush: WebSocket not connected or no session');
        return;
    }

    if (pcmChunks.length === 0) {
        return;
    }

    try {
        // Concatenate all PCM chunks
        const totalLength = pcmChunks.reduce((sum, chunk) => sum + chunk.length, 0);
        const combined = new Int16Array(totalLength);

        let offset = 0;
        for (const chunk of pcmChunks) {
            combined.set(chunk, offset);
            offset += chunk.length;
        }

        // Convert to base64
        const base64 = arrayBufferToBase64(combined.buffer);

        // Send flush message
        wsClient.send({
            type: 'flush',
            data: base64,
        });

        // Calculate duration for logging
        const durationSec = totalLength / 16000;  // 16kHz sample rate
        console.log(`Flushed ${pcmChunks.length} chunks (${durationSec.toFixed(1)}s) to server`);

        // Clear chunks that were flushed but keep recent ones for context
        // Keep last ~2 seconds of audio for overlap (about 8 chunks at 4096 samples each)
        const keepCount = Math.min(8, pcmChunks.length);
        pcmChunks = pcmChunks.slice(-keepCount);

        lastFlushTime = Date.now();

        // Also trim MediaRecorder chunks to prevent browser memory bloat
        if (recordedChunks.length > MAX_BROWSER_CHUNKS) {
            console.log(`Trimming browser audio buffer from ${recordedChunks.length} to ${MAX_BROWSER_CHUNKS} chunks`);
            recordedChunks = recordedChunks.slice(-MAX_BROWSER_CHUNKS);
        }

    } catch (error) {
        console.error('Error flushing chunks to server:', error);
    }
}

/**
 * Get current recording statistics.
 */
function getRecordingStats() {
    const elapsedMs = recordingStartTime ? Date.now() - recordingStartTime : 0;
    const browserChunks = recordedChunks.length;
    const pcmChunkCount = pcmChunks.length;

    return {
        elapsedMs,
        elapsedFormatted: formatElapsedTime(elapsedMs),
        browserChunks,
        pcmChunks: pcmChunkCount,
        sessionId,
        lastFlushTime,
    };
}

/**
 * Format elapsed time in HH:MM:SS format.
 */
function formatElapsedTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}
