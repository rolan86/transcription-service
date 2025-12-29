/**
 * File upload handler for batch transcription.
 */

let uploaderElements = {};

/**
 * Initialize the uploader.
 */
function initUploader() {
    uploaderElements.uploadZone = document.getElementById('upload-zone');
    uploaderElements.fileInput = document.getElementById('file-input');
    uploaderElements.fileInfo = document.getElementById('file-info');
    uploaderElements.fileName = uploaderElements.fileInfo.querySelector('.file-name');
    uploaderElements.removeFile = document.getElementById('remove-file');
    uploaderElements.transcribeBtn = document.getElementById('transcribe-btn');

    setupUploaderEvents();
}

/**
 * Set up uploader event listeners.
 */
function setupUploaderEvents() {
    // Click to browse
    uploaderElements.uploadZone.addEventListener('click', () => {
        uploaderElements.fileInput.click();
    });

    // File input change
    uploaderElements.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // Drag and drop
    uploaderElements.uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploaderElements.uploadZone.classList.add('dragover');
    });

    uploaderElements.uploadZone.addEventListener('dragleave', () => {
        uploaderElements.uploadZone.classList.remove('dragover');
    });

    uploaderElements.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploaderElements.uploadZone.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    // Remove file
    uploaderElements.removeFile.addEventListener('click', () => {
        resetUploader();
    });

    // Transcribe button
    uploaderElements.transcribeBtn.addEventListener('click', startTranscription);
}

/**
 * Handle file selection.
 */
function handleFileSelect(file) {
    // Validate file type
    const validExtensions = ['.mp3', '.wav', '.m4a', '.flac', '.mp4', '.mov', '.avi'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
        showError(`Unsupported file format: ${ext}`);
        return;
    }

    // Store file
    AppState.selectedFile = file;

    // Update UI
    uploaderElements.fileName.textContent = `${file.name} (${formatFileSize(file.size)})`;
    uploaderElements.fileInfo.hidden = false;
    uploaderElements.uploadZone.hidden = true;
    uploaderElements.transcribeBtn.disabled = false;
}

/**
 * Format file size for display.
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Reset the uploader.
 */
function resetUploader() {
    AppState.selectedFile = null;
    uploaderElements.fileInput.value = '';
    uploaderElements.fileInfo.hidden = true;
    uploaderElements.uploadZone.hidden = false;
    uploaderElements.transcribeBtn.disabled = true;
}

/**
 * Start transcription of the selected file.
 */
async function startTranscription() {
    if (!AppState.selectedFile || AppState.isProcessing) return;

    AppState.isProcessing = true;
    uploaderElements.transcribeBtn.disabled = true;
    hideError();
    showProgress('Uploading file...', 10);

    try {
        // Create form data
        const formData = new FormData();
        formData.append('file', AppState.selectedFile);
        formData.append('output_format', AppState.settings.outputFormat);
        formData.append('model', AppState.settings.model);
        formData.append('enable_speakers', AppState.settings.enableSpeakers);
        formData.append('async_mode', 'true');

        if (AppState.settings.language) {
            formData.append('language', AppState.settings.language);
        }

        // Submit transcription request
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start transcription');
        }

        const data = await response.json();
        AppState.currentJob = data.job_id;

        // Poll for job status
        updateProgress('Processing audio...', 30);
        await pollJobStatus(data.job_id);

    } catch (error) {
        showError(error.message);
        hideProgress();
    } finally {
        AppState.isProcessing = false;
        uploaderElements.transcribeBtn.disabled = false;
    }
}

/**
 * Poll for job status until completion.
 */
async function pollJobStatus(jobId) {
    const pollInterval = 1000; // 1 second
    const maxPolls = 600; // 10 minutes max
    let polls = 0;

    while (polls < maxPolls) {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);

            if (!response.ok) {
                throw new Error('Failed to get job status');
            }

            const job = await response.json();

            // Update progress
            const progress = 30 + (job.progress * 60);
            updateProgress(`Processing... ${Math.round(job.progress * 100)}%`, progress);

            if (job.status === 'completed') {
                // Get result
                updateProgress('Fetching results...', 95);
                const resultResponse = await fetch(`/api/jobs/${jobId}/result`);

                if (!resultResponse.ok) {
                    throw new Error('Failed to get transcription result');
                }

                const result = await resultResponse.json();
                showResults(result);
                return;

            } else if (job.status === 'failed') {
                throw new Error(job.error || 'Transcription failed');
            }

            // Wait before next poll
            await new Promise(resolve => setTimeout(resolve, pollInterval));
            polls++;

        } catch (error) {
            throw error;
        }
    }

    throw new Error('Transcription timed out');
}
