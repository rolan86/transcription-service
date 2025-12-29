/**
 * Audio recorder for real-time transcription.
 * Uses Web Audio API for PCM capture and MediaRecorder for saving.
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

// For saving audio
let recordedChunks = [];
let recordedAudioBlob = null;

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
        await wsClient.connect();

        // Start streaming config
        wsClient.send({
            type: 'start',
            model: AppState.settings.model,
            language: AppState.settings.language || null,
            sample_rate: 16000,
        });

        // Process audio data for streaming
        scriptProcessor.onaudioprocess = (event) => {
            if (wsClient && wsClient.isConnected) {
                const inputData = event.inputBuffer.getChannelData(0);

                // Convert Float32 to Int16 PCM
                const pcmData = float32ToInt16(inputData);

                // Convert to base64 and send
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
 * Download the recorded audio file.
 */
function downloadRecordedAudio() {
    if (!recordedAudioBlob) {
        showError('No recording available to download');
        return;
    }

    const url = URL.createObjectURL(recordedAudioBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `recording_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.webm`;
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
 */
function startTimer() {
    timerInterval = setInterval(() => {
        const elapsed = Date.now() - recordingStartTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        recorderElements.recordTimer.textContent =
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
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
