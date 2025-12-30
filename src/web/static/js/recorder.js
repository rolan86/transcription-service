/**
 * Audio recorder for real-time transcription.
 * Uses Web Audio API for PCM capture and MediaRecorder for saving.
 * Supports long recordings (1+ hours) with server-side chunk persistence.
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

    setupRecorderEvents();
}

/**
 * Set up recorder event listeners.
 */
function setupRecorderEvents() {
    recorderElements.recordBtn.addEventListener('click', toggleRecording);
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
    try {
        // Reset state
        recordedChunks = [];
        recordedAudioBlob = null;
        pcmChunks = [];
        sessionId = null;
        lastFlushTime = Date.now();

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

        // Handle session_id from ready message
        const originalOnReady = wsClient.onReady;
        wsClient.onReady = (message) => {
            if (message.session_id) {
                sessionId = message.session_id;
                console.log('Recording session started:', sessionId);
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

    // Clean up audio context
    if (audioContext) {
        audioContext.close();
        audioContext = null;
        analyser = null;
    }

    // Update UI
    recorderElements.recordBtn.classList.remove('recording');
    recorderElements.recordText.textContent = 'Start Recording';
    recorderElements.levelBar.style.width = '0%';

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
 */
function startTimer() {
    timerInterval = setInterval(() => {
        const elapsed = Date.now() - recordingStartTime;
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
