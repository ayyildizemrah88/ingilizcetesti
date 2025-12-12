/**
 * ══════════════════════════════════════════════════════════════
 * SPEAKING RECORDER - WebRTC Audio Recording for Speaking Tests
 * ══════════════════════════════════════════════════════════════
 * Uses MediaRecorder API to capture candidate speech
 */

class SpeakingRecorder {
    constructor(options = {}) {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        this.isRecording = false;
        this.isPaused = false;
        this.startTime = null;
        this.maxDuration = options.maxDuration || 120; // 2 minutes default
        this.onStop = options.onStop || (() => { });
        this.onError = options.onError || console.error;
        this.onTimeUpdate = options.onTimeUpdate || (() => { });
        this.timerInterval = null;
    }

    async checkPermission() {
        try {
            const result = await navigator.permissions.query({ name: 'microphone' });
            return result.state;
        } catch (e) {
            return 'prompt';
        }
    }

    async requestAccess() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100
                }
            });
            return true;
        } catch (error) {
            this.onError('Microphone access denied: ' + error.message);
            return false;
        }
    }

    async start() {
        if (this.isRecording) {
            return false;
        }

        if (!this.stream) {
            const hasAccess = await this.requestAccess();
            if (!hasAccess) return false;
        }

        this.audioChunks = [];

        // Prefer webm/opus for better quality, fallback to alternatives
        const mimeTypes = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4'
        ];

        let mimeType = '';
        for (const type of mimeTypes) {
            if (MediaRecorder.isTypeSupported(type)) {
                mimeType = type;
                break;
            }
        }

        try {
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: mimeType || undefined,
                audioBitsPerSecond: 128000
            });

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.isRecording = false;
                clearInterval(this.timerInterval);
                const audioBlob = new Blob(this.audioChunks, { type: mimeType || 'audio/webm' });
                this.onStop(audioBlob);
            };

            this.mediaRecorder.onerror = (event) => {
                this.onError('Recording error: ' + event.error);
            };

            this.mediaRecorder.start(1000); // Collect data every second
            this.isRecording = true;
            this.startTime = Date.now();

            // Start timer
            this.timerInterval = setInterval(() => {
                const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
                this.onTimeUpdate(elapsed, this.maxDuration);

                if (elapsed >= this.maxDuration) {
                    this.stop();
                }
            }, 1000);

            return true;
        } catch (error) {
            this.onError('Failed to start recording: ' + error.message);
            return false;
        }
    }

    stop() {
        if (!this.isRecording || !this.mediaRecorder) {
            return false;
        }

        this.mediaRecorder.stop();
        return true;
    }

    pause() {
        if (this.isRecording && this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.pause();
            this.isPaused = true;
            return true;
        }
        return false;
    }

    resume() {
        if (this.isPaused && this.mediaRecorder && this.mediaRecorder.state === 'paused') {
            this.mediaRecorder.resume();
            this.isPaused = false;
            return true;
        }
        return false;
    }

    destroy() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
        }
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        clearInterval(this.timerInterval);
    }

    getElapsedTime() {
        if (!this.startTime) return 0;
        return Math.floor((Date.now() - this.startTime) / 1000);
    }
}

/**
 * Upload audio blob to server
 */
async function uploadSpeakingAudio(blob, questionId, csrfToken) {
    const formData = new FormData();
    formData.append('audio', blob, 'speaking_answer.webm');
    formData.append('question_id', questionId);

    try {
        const response = await fetch('/api/speaking/upload', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        return await response.json();
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

/**
 * Convert blob to base64 for storage
 */
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

/**
 * Format seconds to MM:SS
 */
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Initialize speaking test UI
 */
function initSpeakingTest(containerId, questionId, csrfToken) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const statusEl = container.querySelector('.recording-status');
    const timerEl = container.querySelector('.recording-timer');
    const startBtn = container.querySelector('.btn-start-recording');
    const stopBtn = container.querySelector('.btn-stop-recording');
    const previewEl = container.querySelector('.audio-preview');
    const uploadStatusEl = container.querySelector('.upload-status');

    let recorder = null;

    startBtn.addEventListener('click', async () => {
        recorder = new SpeakingRecorder({
            maxDuration: 120,
            onStop: async (blob) => {
                statusEl.textContent = 'Recording complete';
                statusEl.classList.remove('recording');
                stopBtn.disabled = true;
                startBtn.disabled = false;

                // Show preview
                const audioUrl = URL.createObjectURL(blob);
                previewEl.innerHTML = `
                    <audio controls src="${audioUrl}"></audio>
                    <p class="text-muted">Duration: ${formatTime(recorder.getElapsedTime())}</p>
                `;

                // Upload
                uploadStatusEl.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Uploading...';
                try {
                    const result = await uploadSpeakingAudio(blob, questionId, csrfToken);
                    uploadStatusEl.innerHTML = '<span class="text-success">✓ Uploaded successfully</span>';

                    if (result.transcript) {
                        uploadStatusEl.innerHTML += `<p class="mt-2"><strong>Transcript:</strong> ${result.transcript}</p>`;
                    }
                    if (result.score) {
                        uploadStatusEl.innerHTML += `<p><strong>AI Score:</strong> ${result.score}/100</p>`;
                    }
                } catch (error) {
                    uploadStatusEl.innerHTML = '<span class="text-danger">✗ Upload failed. Your answer was saved locally.</span>';
                    // Save to localStorage as backup
                    const base64 = await blobToBase64(blob);
                    localStorage.setItem(`speaking_${questionId}`, JSON.stringify({
                        audio: base64,
                        timestamp: Date.now()
                    }));
                }
            },
            onTimeUpdate: (elapsed, max) => {
                timerEl.textContent = `${formatTime(elapsed)} / ${formatTime(max)}`;
                const progress = (elapsed / max) * 100;
                timerEl.style.setProperty('--progress', progress + '%');
            },
            onError: (error) => {
                statusEl.textContent = 'Error: ' + error;
                statusEl.classList.add('error');
            }
        });

        const started = await recorder.start();
        if (started) {
            statusEl.textContent = 'Recording...';
            statusEl.classList.add('recording');
            startBtn.disabled = true;
            stopBtn.disabled = false;
        }
    });

    stopBtn.addEventListener('click', () => {
        if (recorder) {
            recorder.stop();
        }
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (recorder) {
            recorder.destroy();
        }
    });
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SpeakingRecorder, uploadSpeakingAudio, formatTime, initSpeakingTest };
}
