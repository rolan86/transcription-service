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

        // Callbacks for long recording support
        this.onReady = null;
        this.onFlushAck = null;
        this.onSessionStats = null;
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
                    if (message.session_id) {
                        console.log('Session ID:', message.session_id);
                    }
                    // Call callback if set
                    if (this.onReady) {
                        this.onReady(message);
                    }
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
                        updateLiveTranscript(message.message || 'Processing final transcription...');
                    }
                    break;

                case 'flush_ack':
                    // Acknowledgment that server received and stored flushed audio
                    if (message.success) {
                        console.log(`Flush acknowledged: ${message.chunk_count} chunks, ${message.total_duration?.toFixed(1)}s total`);
                    } else {
                        console.error('Flush failed:', message.error);
                    }
                    if (this.onFlushAck) {
                        this.onFlushAck(message);
                    }
                    break;

                case 'session_stats':
                    // Session statistics from server
                    console.log('Session stats:', message);
                    if (this.onSessionStats) {
                        this.onSessionStats(message);
                    }
                    break;

                case 'error':
                    console.error('Server error:', message.error);
                    showError(message.error);
                    break;

                case 'pong':
                case 'ping':
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

        // Log session duration for long recordings
        if (message.session_duration) {
            const minutes = Math.floor(message.session_duration / 60);
            const seconds = Math.floor(message.session_duration % 60);
            console.log(`Recording session duration: ${minutes}m ${seconds}s`);
        }

        // Show final result
        const result = {
            text: message.text || this.fullTranscript.trim(),
            language: 'auto',
            confidence: 0.9,
            processing_time: 0,
            segments: message.segments || [],
            session_duration: message.session_duration || 0,
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
