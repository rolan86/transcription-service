/**
 * WebSocket client for real-time transcription.
 */

class TranscriptionWebSocket {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.fullTranscript = '';
    }

    /**
     * Connect to the WebSocket server.
     */
    async connect() {
        return new Promise((resolve, reject) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = `${protocol}//${window.location.host}/ws/transcribe`;

            this.socket = new WebSocket(url);

            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                resolve();
            };

            this.socket.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.isConnected = false;

                // If we have accumulated transcript, show it even if connection closed unexpectedly
                if (this.fullTranscript.trim() && !event.wasClean) {
                    console.log('Connection closed unexpectedly, showing accumulated transcript');
                    const result = {
                        text: this.fullTranscript.trim(),
                        language: 'auto',
                        confidence: 0.8,
                        processing_time: 0,
                        segments: [],
                    };

                    if (typeof hideLiveTranscript === 'function') {
                        hideLiveTranscript();
                    }
                    showResults(result);
                    if (typeof showRecordingActions === 'function') {
                        showRecordingActions();
                    }
                }
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            this.socket.onmessage = (event) => {
                this.handleMessage(event.data);
            };
        });
    }

    /**
     * Send a message to the server.
     */
    send(data) {
        if (this.socket && this.isConnected) {
            this.socket.send(JSON.stringify(data));
        }
    }

    /**
     * Handle incoming messages.
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data);

            switch (message.type) {
                case 'ready':
                    console.log('Transcriber ready:', message.message);
                    break;

                case 'transcript':
                    this.handleTranscript(message);
                    break;

                case 'complete':
                    this.handleComplete(message);
                    break;

                case 'status':
                    console.log('Status:', message.status, message.message);
                    // Show processing status to user
                    if (message.status === 'processing') {
                        updateLiveTranscript('Processing final transcription...');
                    }
                    break;

                case 'error':
                    console.error('Server error:', message.error);
                    showError(message.error);
                    break;

                case 'pong':
                    // Keep-alive response
                    break;

                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    }

    /**
     * Handle transcript update.
     */
    handleTranscript(message) {
        if (message.text) {
            // Append to full transcript
            this.fullTranscript += ' ' + message.text;

            // Update live display
            updateLiveTranscript(this.fullTranscript.trim());
        }
    }

    /**
     * Handle transcription complete.
     */
    handleComplete(message) {
        console.log('Transcription complete:', message);

        // Show final result
        const result = {
            text: message.text || this.fullTranscript.trim(),
            language: 'auto',
            confidence: 0.9,
            processing_time: 0,
            segments: message.segments || [],
        };

        // Hide live transcript, show results
        if (typeof hideLiveTranscript === 'function') {
            hideLiveTranscript();
        }

        // Show results and recording actions
        showResults(result);

        // Show download buttons for recording mode
        if (typeof showRecordingActions === 'function') {
            showRecordingActions();
        }

        // Now close the WebSocket connection
        this.close();
    }

    /**
     * Close the WebSocket connection.
     */
    close() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        this.isConnected = false;
        this.fullTranscript = '';
    }

    /**
     * Send keep-alive ping.
     */
    ping() {
        this.send({ type: 'ping' });
    }
}
