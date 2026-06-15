/**
 * Speech Recognition – Frontend Logic
 * ====================================
 * Handles:
 *  - File upload (wav, mp3, webm, ogg, flac, m4a)
 *  - Microphone recording via MediaRecorder API
 *  - Sending audio to /predict and rendering results
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM References ---
    const fileInput       = document.getElementById('file-input');
    const fileLabel       = document.getElementById('file-label');
    const fileName        = document.getElementById('file-name');
    const recordBtn       = document.getElementById('record-btn');
    const recordStatus    = document.getElementById('record-status');
    const previewSection  = document.getElementById('preview-section');
    const audioPreview    = document.getElementById('audio-preview');
    const analyzeBtn      = document.getElementById('analyze-btn');
    const loading         = document.getElementById('loading');
    const resultBox       = document.getElementById('result-box');
    const inputBox        = document.getElementById('input-box');

    // Result elements
    const transcriptionText  = document.getElementById('transcription-text');
    const transcriptionCard  = document.getElementById('transcription-card');
    const predictionBadge    = document.getElementById('prediction-badge');
    const predictionCard     = document.getElementById('prediction-card');
    const confidenceCard     = document.getElementById('confidence-card');
    const confidenceBar      = document.getElementById('confidence-bar');
    const confidenceText     = document.getElementById('confidence-text');
    const spectrogramBox     = document.getElementById('spectrogram-box');
    const spectrogramImg     = document.getElementById('spectrogram-img');
    const errorText          = document.getElementById('error-text');
    const resetBtn           = document.getElementById('reset-btn');

    let currentAudioFile = null;
    let mediaRecorder    = null;
    let audioChunks      = [];
    let isRecording      = false;


    // =========================================================================
    // FILE UPLOAD
    // =========================================================================
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            currentAudioFile = file;
            fileName.textContent = file.name;
            audioPreview.src = URL.createObjectURL(file);
            previewSection.style.display = 'block';
            resultBox.style.display = 'none';
        }
    });


    // =========================================================================
    // MICROPHONE RECORDING
    // =========================================================================
    recordBtn.addEventListener('click', async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

                // Pick a MIME type the browser supports
                const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus'
                    : 'audio/webm';

                mediaRecorder = new MediaRecorder(stream, { mimeType });
                audioChunks = [];

                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) audioChunks.push(e.data);
                };

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: mimeType });
                    // Give it a .webm extension so the backend knows the format
                    currentAudioFile = new File([audioBlob], 'recording.webm', { type: mimeType });

                    audioPreview.src = URL.createObjectURL(currentAudioFile);
                    previewSection.style.display = 'block';
                    resultBox.style.display = 'none';

                    // Release microphone
                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                isRecording = true;
                recordBtn.textContent = '⏹ Stop Recording';
                recordBtn.classList.add('recording');
                recordStatus.textContent = '🔴 Recording…';
                recordStatus.style.color = '#e74c3c';
            } catch (err) {
                console.error('Microphone access error:', err);
                alert('Microphone access denied or unavailable.\nPlease check browser permissions.');
            }
        } else {
            // Stop
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            isRecording = false;
            recordBtn.textContent = 'Start Recording';
            recordBtn.classList.remove('recording');
            recordStatus.textContent = '✅ Recording saved';
            recordStatus.style.color = '#27ae60';
        }
    });


    // =========================================================================
    // ANALYZE – send to /predict
    // =========================================================================
    analyzeBtn.addEventListener('click', async () => {
        if (!currentAudioFile) {
            alert('Please upload or record an audio file first.');
            return;
        }

        const formData = new FormData();
        formData.append('audio', currentAudioFile);

        // Show loading, hide previous results
        loading.style.display = 'block';
        resultBox.style.display = 'none';
        errorText.style.display = 'none';

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData,
            });

            let data;
            try {
                data = await response.json();
            } catch (_) {
                throw new Error('Invalid response from server.');
            }

            loading.style.display = 'none';
            resultBox.style.display = 'block';

            if (data.success) {
                // --- Transcription ---
                transcriptionText.textContent = data.transcription || '(no speech detected)';
                transcriptionCard.style.display = 'block';

                // --- Prediction Badge ---
                predictionBadge.textContent = data.prediction;
                predictionBadge.className = 'badge ' + data.prediction.toLowerCase();
                predictionCard.style.display = 'block';

                // --- Confidence ---
                if (data.confidence) {
                    const pct = parseFloat(data.confidence);
                    confidenceBar.style.width = pct + '%';
                    confidenceText.textContent = data.confidence;
                    confidenceCard.style.display = 'block';
                } else {
                    confidenceCard.style.display = 'none';
                }

                // --- Spectrogram ---
                if (data.spectrogram) {
                    spectrogramImg.src = data.spectrogram;
                    spectrogramBox.style.display = 'block';
                } else {
                    spectrogramBox.style.display = 'none';
                }

                errorText.style.display = 'none';
            } else {
                // Backend returned success: false
                transcriptionCard.style.display = 'none';
                predictionCard.style.display = 'none';
                confidenceCard.style.display = 'none';
                spectrogramBox.style.display = 'none';
                errorText.textContent = data.error || 'Unknown error occurred.';
                errorText.style.display = 'block';
            }
        } catch (err) {
            console.error('Connection or processing error:', err);
            loading.style.display = 'none';
            resultBox.style.display = 'block';

            transcriptionCard.style.display = 'none';
            predictionCard.style.display = 'none';
            confidenceCard.style.display = 'none';
            spectrogramBox.style.display = 'none';
            errorText.textContent = err.message || 'Could not connect to the server.';
            errorText.style.display = 'block';
        }
    });


    // =========================================================================
    // RESET
    // =========================================================================
    resetBtn.addEventListener('click', () => {
        resultBox.style.display = 'none';
        previewSection.style.display = 'none';
        fileInput.value = '';
        fileName.textContent = '';
        currentAudioFile = null;
        recordStatus.textContent = 'Not recording';
        recordStatus.style.color = '#777777';
    });
});
