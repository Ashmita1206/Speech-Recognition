/**
 * Speech Recognition Studio — Frontend Logic
 * ============================================
 * Pure Speech-to-Text Studio application handling:
 *  - Microphone voice recording via MediaRecorder API
 *  - Live audio waveform canvas visualization
 *  - Audio file upload (drag & drop and file picker)
 *  - Backend Faster-Whisper integration via /transcribe
 *  - Transcript display, copy (with toast feedback), and .txt download
 *  - Workspace clear/reset
 *  - Local browser transcription history
 */

document.addEventListener('DOMContentLoaded', () => {
    // =========================================================================
    // 1. STATE & CONSTANTS
    // =========================================================================
    const STORAGE_KEY_HISTORY = 'speech_studio_history_v1';

    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let recordingStartTime = null;
    let recordingTimerInterval = null;

    let audioContext = null;
    let analyser = null;
    let animationFrameId = null;

    let selectedUploadFile = null;
    let currentTranscription = '';
    let currentMetadata = { language: '—', duration: '—', processingTime: '—' };

    // Translation state
    let lastTranscription = '';
    let lastSourceLanguage = 'en';
    let currentTranslationData = null; // { sourceText, translatedText, targetLanguage, sourceLanguage }
    let lastAttemptedTargetLanguage = 'Hindi';
    let isSpeaking = false;

    // =========================================================================
    // 2. DOM REFERENCES
    // =========================================================================
    // Status & Error
    const statusBanner = document.getElementById('status-banner');
    const statusMessage = document.getElementById('status-message');
    const errorNotice = document.getElementById('error-notice');
    const errorTitle = document.getElementById('error-title');
    const errorDesc = document.getElementById('error-desc');
    const btnCloseError = document.getElementById('btn-close-error');
    const toastContainer = document.getElementById('toast-container');

    // Navigation
    const btnScrollHistory = document.getElementById('btn-scroll-history');
    const btnResetWorkspace = document.getElementById('btn-reset-workspace');

    // Recording Card
    const recordReadyView = document.getElementById('record-ready-view');
    const recordActiveView = document.getElementById('record-active-view');
    const btnStartRecord = document.getElementById('btn-start-record');
    const btnStopRecord = document.getElementById('btn-stop-record');
    const btnCancelRecord = document.getElementById('btn-cancel-record');
    const recordingTimer = document.getElementById('recording-timer');
    const waveformCanvas = document.getElementById('waveform-canvas');

    // Upload Card
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const filePreviewCard = document.getElementById('file-preview-card');
    const previewFilename = document.getElementById('preview-filename');
    const previewFilesize = document.getElementById('preview-filesize');
    const btnRemoveFile = document.getElementById('btn-remove-file');
    const btnTranscribeFile = document.getElementById('btn-transcribe-file');

    // Transcript Section
    const transcriptSection = document.getElementById('transcript-section');
    const transcriptText = document.getElementById('transcript-text');
    const transcriptStatusBadge = document.getElementById('transcript-status-badge');
    const btnCopyTranscript = document.getElementById('btn-copy-transcript');
    const copyBtnText = document.getElementById('copy-btn-text');
    const btnDownloadTranscript = document.getElementById('btn-download-transcript');
    const btnClearTranscript = document.getElementById('btn-clear-transcript');

    // Metadata Bar
    const metaLanguage = document.getElementById('meta-language');
    const metaDuration = document.getElementById('meta-duration');
    const metaProcessing = document.getElementById('meta-processing');

    // Translation Elements
    const translationOfferBox = document.getElementById('translation-offer-box');
    const btnOfferTranslate = document.getElementById('btn-offer-translate');
    const btnOfferSkip = document.getElementById('btn-offer-skip');

    const translationSelectorBox = document.getElementById('translation-selector-box');
    const targetLanguageSelect = document.getElementById('target-language-select');
    const otherLanguageWrapper = document.getElementById('other-language-wrapper');
    const otherLanguageInput = document.getElementById('other-language-input');
    const btnTriggerTranslate = document.getElementById('btn-trigger-translate');
    const triggerTranslateText = document.getElementById('trigger-translate-text');
    const btnCloseSelector = document.getElementById('btn-close-selector');

    const translationErrorNotice = document.getElementById('translation-error-notice');
    const translationErrorMsg = document.getElementById('translation-error-msg');
    const btnRetryTranslate = document.getElementById('btn-retry-translate');

    const translationDisplayCard = document.getElementById('translation-display-card');
    const translationRouteText = document.getElementById('translation-route-text');
    const btnCopyTranslation = document.getElementById('btn-copy-translation');
    const copyTranslationBtnText = document.getElementById('copy-translation-btn-text');
    const btnDownloadTranslation = document.getElementById('btn-download-translation');
    const btnListenTranslation = document.getElementById('btn-listen-translation');
    const listenTranslationBtnText = document.getElementById('listen-translation-btn-text');
    const btnRetranslate = document.getElementById('btn-retranslate');
    const transOriginalContent = document.getElementById('trans-original-content');
    const transTargetTitle = document.getElementById('trans-target-title');
    const transTargetContent = document.getElementById('trans-target-content');

    // History Section
    const historySection = document.getElementById('history-section');
    const historyList = document.getElementById('history-list');
    const historyEmptyPlaceholder = document.getElementById('history-empty-placeholder');
    const btnClearHistory = document.getElementById('btn-clear-history');

    // =========================================================================
    // 3. INITIALIZATION
    // =========================================================================
    function init() {
        renderHistoryList();
        setupEventListeners();
    }

    // =========================================================================
    // 4. MICROPHONE RECORDING WORKFLOW
    // =========================================================================
    async function startRecording() {
        hideError();
        hideStatus();

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showError('Microphone not supported', 'Your browser does not support audio recording.');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm';

            mediaRecorder = new MediaRecorder(stream, { mimeType });
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // Stop audio tracks
                stream.getTracks().forEach(track => track.stop());
                stopWaveform();

                if (audioChunks.length === 0) {
                    resetRecordingUI();
                    return;
                }

                const audioBlob = new Blob(audioChunks, { type: mimeType });
                const audioFile = new File([audioBlob], 'microphone_recording.webm', { type: mimeType });
                
                resetRecordingUI();
                await sendAudioToTranscribe(audioFile, 'Microphone Recording');
            };

            mediaRecorder.start();
            isRecording = true;

            // Update UI to Active Recording State
            recordReadyView.style.display = 'none';
            recordActiveView.style.display = 'flex';
            recordingTimer.textContent = '00:00';
            recordingStartTime = Date.now();

            clearInterval(recordingTimerInterval);
            recordingTimerInterval = setInterval(() => {
                const elapsedSec = Math.floor((Date.now() - recordingStartTime) / 1000);
                recordingTimer.textContent = formatDuration(elapsedSec);
            }, 1000);

            // Start Audio Waveform Canvas Visualizer
            startWaveform(stream);

        } catch (err) {
            console.error('Microphone error:', err);
            resetRecordingUI();
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                showError('Microphone access denied', 'Please allow microphone access in your browser settings and try again.');
            } else {
                showError('Microphone unavailable', 'Could not initialize microphone. Please check your audio device.');
            }
        }
    }

    function stopRecording() {
        if (!isRecording || !mediaRecorder) return;
        showStatus('Processing audio...');
        mediaRecorder.stop();
        isRecording = false;
        clearInterval(recordingTimerInterval);
    }

    function cancelRecording() {
        if (!isRecording) return;
        audioChunks = [];
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        isRecording = false;
        clearInterval(recordingTimerInterval);
        stopWaveform();
        resetRecordingUI();
        hideStatus();
        stopSpeechSynthesis();
    }

    function resetRecordingUI() {
        recordActiveView.style.display = 'none';
        recordReadyView.style.display = 'flex';
        recordingTimer.textContent = '00:00';
        clearInterval(recordingTimerInterval);
        stopWaveform();
    }

    // =========================================================================
    // 5. WAVEFORM AUDIO VISUALIZATION
    // =========================================================================
    function startWaveform(stream) {
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            const source = audioContext.createMediaStreamSource(stream);
            source.connect(analyser);
            analyser.fftSize = 64;

            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            const ctx = waveformCanvas.getContext('2d');

            function draw() {
                animationFrameId = requestAnimationFrame(draw);
                analyser.getByteFrequencyData(dataArray);

                const width = waveformCanvas.width;
                const height = waveformCanvas.height;
                ctx.clearRect(0, 0, width, height);

                const barWidth = Math.floor(width / bufferLength) - 1;
                let x = 2;

                for (let i = 0; i < bufferLength; i++) {
                    const barHeight = Math.max(3, (dataArray[i] / 255) * height * 0.85);
                    const y = (height - barHeight) / 2;

                    ctx.fillStyle = '#1e3a8a';
                    ctx.fillRect(x, y, barWidth, barHeight);
                    x += barWidth + 2;
                }
            }
            draw();
        } catch (e) {
            console.warn('Waveform audio visualizer error:', e);
        }
    }

    function stopWaveform() {
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        if (audioContext && audioContext.state !== 'closed') {
            audioContext.close();
            audioContext = null;
        }
    }

    // =========================================================================
    // 6. AUDIO FILE UPLOAD WORKFLOW
    // =========================================================================
    function handleFileSelection(file) {
        hideError();
        if (!file) return;

        const allowedExtensions = ['wav', 'mp3', 'm4a', 'webm', 'flac', 'ogg'];
        const ext = file.name.split('.').pop().toLowerCase();

        if (!allowedExtensions.includes(ext)) {
            showError('Unsupported audio format', `File extension ".${ext}" is not supported. Please choose a WAV, MP3, M4A, WebM, FLAC, or OGG file.`);
            return;
        }

        selectedUploadFile = file;
        previewFilename.textContent = file.name;
        previewFilesize.textContent = formatFileSize(file.size);

        dropzone.style.display = 'none';
        filePreviewCard.style.display = 'flex';
    }

    function removeSelectedFile() {
        selectedUploadFile = null;
        fileInput.value = '';
        filePreviewCard.style.display = 'none';
        dropzone.style.display = 'flex';
    }

    // =========================================================================
    // 7. SEND TO BACKEND (/transcribe)
    // =========================================================================
    async function sendAudioToTranscribe(file, defaultTitle = 'Audio File') {
        hideError();
        showStatus('Transcribing speech...');
        setControlsDisabled(true);

        const formData = new FormData();
        formData.append('audio', file);

        try {
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });

            let data;
            try {
                data = await response.json();
            } catch (jsonErr) {
                throw new Error('Unexpected response format from server.');
            }

            hideStatus();
            setControlsDisabled(false);

            if (response.ok && data.status === 'success') {
                const text = (data.transcription || '').trim();

                if (!text) {
                    showError('No speech detected', 'Faster-Whisper did not detect readable speech in the audio.');
                    return;
                }

                // Check if this transcribed audio is a voice translation command
                const voiceTargetLang = detectVoiceTranslationCommand(text);

                if (voiceTargetLang) {
                    // Use the most recent transcription as the source text
                    const sourceTextToTranslate = (lastTranscription || transcriptText.value || '').trim();

                    if (!sourceTextToTranslate) {
                        showError('Please record something first.', 'There is no previous transcription available to translate.');
                        showToast('Please record something first.');
                        return;
                    }

                    // Directly translate the latest transcription into the requested language
                    showToast(`Voice command detected: translating to ${voiceTargetLang}`);
                    executeTranslation(sourceTextToTranslate, voiceTargetLang, lastSourceLanguage);
                    return;
                }

                // Standard speech transcription
                currentTranscription = text;
                lastTranscription = text;
                lastSourceLanguage = data.language || 'en';

                transcriptText.value = text;
                transcriptStatusBadge.textContent = 'Completed';
                transcriptStatusBadge.style.color = 'var(--success)';

                // Update metadata
                const lang = (data.language || 'en').toUpperCase();
                const dur = data.duration ? formatDuration(Math.round(data.duration)) : '—';
                const proc = data.processing_time ? `${data.processing_time}s` : '—';

                metaLanguage.textContent = lang;
                metaDuration.textContent = dur;
                metaProcessing.textContent = proc;

                currentMetadata = { language: lang, duration: dur, processingTime: proc };

                // Enable action buttons
                btnCopyTranscript.disabled = false;
                btnDownloadTranscript.disabled = false;
                btnClearTranscript.disabled = false;

                // Reset previous translation card and display offer prompt
                hideTranslationResult();
                hideTranslationSelector();
                hideTranslationError();
                showTranslationOffer();

                // Save to local history
                saveHistoryItem({
                    id: 'tx-' + Date.now(),
                    title: file.name.replace(/\.[^/.]+$/, '') || defaultTitle,
                    text: text,
                    language: lang,
                    duration: dur,
                    processingTime: proc,
                    timestamp: Date.now()
                });

                // Scroll down to transcript
                transcriptSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            } else {
                const errMsg = data.error || 'The audio could not be transcribed.';
                showError('Transcription failed', errMsg);
            }

        } catch (err) {
            console.error('Request failed:', err);
            hideStatus();
            setControlsDisabled(false);
            showError('Something went wrong', 'Could not complete transcription. Please ensure the server is running and try again.');
        }
    }

    // =========================================================================
    // 8. TRANSCRIPT ACTIONS (Copy, Download, Clear)
    // =========================================================================
    function copyTranscript() {
        const text = transcriptText.value.trim();
        if (!text) return;

        navigator.clipboard.writeText(text).then(() => {
            copyBtnText.textContent = 'Copied';
            showToast('Transcript copied successfully.');
            setTimeout(() => {
                copyBtnText.textContent = 'Copy';
            }, 1800);
        }).catch(() => {
            transcriptText.select();
            document.execCommand('copy');
            showToast('Transcript copied successfully.');
        });
    }

    function downloadTranscript() {
        const text = transcriptText.value.trim();
        if (!text) return;

        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const hh = String(now.getHours()).padStart(2, '0');
        const min = String(now.getMinutes()).padStart(2, '0');
        const ss = String(now.getSeconds()).padStart(2, '0');

        const filename = `transcript_${yyyy}${mm}${dd}_${hh}${min}${ss}.txt`;

        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast(`Downloaded: ${filename}`);
    }

    function clearTranscript() {
        transcriptText.value = '';
        currentTranscription = '';
        lastTranscription = '';
        currentTranslationData = null;
        transcriptStatusBadge.textContent = 'Ready';
        transcriptStatusBadge.style.color = 'var(--text-secondary)';

        metaLanguage.textContent = '—';
        metaDuration.textContent = '—';
        metaProcessing.textContent = '—';

        btnCopyTranscript.disabled = true;
        btnDownloadTranscript.disabled = true;
        btnClearTranscript.disabled = true;

        hideTranslationOffer();
        hideTranslationSelector();
        hideTranslationResult();
        hideTranslationError();
        stopSpeechSynthesis();
    }

    function resetWorkspace() {
        clearTranscript();
        removeSelectedFile();
        cancelRecording();
        hideError();
        hideStatus();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // =========================================================================
    // 9. HISTORY MANAGEMENT (localStorage)
    // =========================================================================
    function loadHistory() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY_HISTORY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function saveHistoryItem(item) {
        const list = loadHistory();
        list.unshift(item);
        // Keep at most 20 items
        if (list.length > 20) list.pop();
        try {
            localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(list));
        } catch (e) {}
        renderHistoryList();
    }

    function renderHistoryList() {
        const items = loadHistory();
        historyList.innerHTML = '';

        if (!items || items.length === 0) {
            historyList.appendChild(historyEmptyPlaceholder);
            historyEmptyPlaceholder.style.display = 'block';
            return;
        }

        historyEmptyPlaceholder.style.display = 'none';

        items.forEach(item => {
            const row = document.createElement('div');
            row.className = 'history-item';
            row.tabIndex = 0;
            row.setAttribute('role', 'button');
            row.setAttribute('aria-label', `Restore transcript for ${item.title}`);

            const dateStr = new Date(item.timestamp).toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            row.innerHTML = `
                <div class="history-item-body">
                    <span class="history-item-title">${escapeHtml(item.title)}</span>
                    <span class="history-item-meta">
                        ${escapeHtml(item.text.slice(0, 80))}${item.text.length > 80 ? '…' : ''} · ${escapeHtml(item.duration)} · ${escapeHtml(dateStr)}
                    </span>
                </div>
                <div class="history-item-actions">
                    <button type="button" class="btn-history-del" title="Delete from history" aria-label="Delete item">Delete</button>
                </div>
            `;

            // Click row to restore transcript
            row.addEventListener('click', (e) => {
                if (e.target.closest('.btn-history-del')) return;
                restoreTranscript(item);
            });

            row.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    if (e.target.closest('.btn-history-del')) return;
                    e.preventDefault();
                    restoreTranscript(item);
                }
            });

            // Delete item button
            row.querySelector('.btn-history-del').addEventListener('click', (e) => {
                e.stopPropagation();
                deleteHistoryItem(item.id);
            });

            historyList.appendChild(row);
        });
    }

    function restoreTranscript(item) {
        transcriptText.value = item.text;
        currentTranscription = item.text;
        lastTranscription = item.text;
        lastSourceLanguage = item.language || 'en';
        transcriptStatusBadge.textContent = 'Restored';
        transcriptStatusBadge.style.color = 'var(--text-secondary)';

        metaLanguage.textContent = item.language || '—';
        metaDuration.textContent = item.duration || '—';
        metaProcessing.textContent = item.processingTime || '—';

        btnCopyTranscript.disabled = false;
        btnDownloadTranscript.disabled = false;
        btnClearTranscript.disabled = false;

        hideTranslationResult();
        hideTranslationSelector();
        hideTranslationError();
        showTranslationOffer();

        transcriptSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        showToast('Transcript loaded from history.');
    }

    function deleteHistoryItem(id) {
        const items = loadHistory().filter(i => i.id !== id);
        try {
            localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(items));
        } catch (e) {}
        renderHistoryList();
    }

    function clearAllHistory() {
        if (!confirm('Are you sure you want to clear transcription history?')) return;
        try {
            localStorage.removeItem(STORAGE_KEY_HISTORY);
        } catch (e) {}
        renderHistoryList();
        showToast('History cleared.');
    }

    // =========================================================================
    // 10. UI NOTIFICATIONS & HELPERS
    // =========================================================================
    function showStatus(msg) {
        statusMessage.textContent = msg;
        statusBanner.style.display = 'flex';
    }

    function hideStatus() {
        statusBanner.style.display = 'none';
    }

    function showError(title, desc) {
        errorTitle.textContent = title;
        errorDesc.textContent = desc;
        errorNotice.style.display = 'flex';
    }

    function hideError() {
        errorNotice.style.display = 'none';
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.remove();
        }, 2200);
    }

    function setControlsDisabled(disabled) {
        btnStartRecord.disabled = disabled;
        btnTranscribeFile.disabled = disabled;
    }

    function formatDuration(seconds) {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // =========================================================================
    // 10.1 TRANSLATION MODULE & VOICE COMMAND WORKFLOW
    // =========================================================================
    const VOICE_TRANSLATE_PATTERNS = [
        /(?:translate|convert)(?:\s+(?:this|it|that|my\s+last\s+transcription|the\s+transcription|the\s+text))?\s+(?:in)?to\s+([a-zA-Z\-]+)/i,
        /give\s+me\s+the\s+([a-zA-Z\-]+)\s+translation/i,
        /give\s+me\s+the\s+translation\s+(?:in|to)\s+([a-zA-Z\-]+)/i,
        /how\s+do\s+you\s+say\s+this\s+in\s+([a-zA-Z\-]+)/i,
        /translate\s+(?:this|it|that)?\s+in\s+([a-zA-Z\-]+)/i,
    ];

    const CANONICAL_LANG_NAMES = {
        'english': 'English',
        'hindi': 'Hindi',
        'spanish': 'Spanish',
        'french': 'French',
        'german': 'German',
        'japanese': 'Japanese',
        'korean': 'Korean',
        'chinese': 'Chinese',
        'arabic': 'Arabic',
        'punjabi': 'Punjabi',
        'bengali': 'Bengali',
        'marathi': 'Marathi',
        'gujarati': 'Gujarati',
        'tamil': 'Tamil',
        'telugu': 'Telugu',
        'kannada': 'Kannada',
        'malayalam': 'Malayalam',
        'italian': 'Italian',
        'portuguese': 'Portuguese',
        'russian': 'Russian',
        'turkish': 'Turkish',
        'dutch': 'Dutch',
    };

    const TTS_LANG_MAP = {
        'hindi': 'hi-IN',
        'english': 'en-US',
        'spanish': 'es-ES',
        'french': 'fr-FR',
        'german': 'de-DE',
        'japanese': 'ja-JP',
        'korean': 'ko-KR',
        'chinese': 'zh-CN',
        'arabic': 'ar-SA',
        'punjabi': 'pa-IN',
        'bengali': 'bn-IN',
        'marathi': 'mr-IN',
        'gujarati': 'gu-IN',
        'tamil': 'ta-IN',
        'telugu': 'te-IN',
        'kannada': 'kn-IN',
        'malayalam': 'ml-IN',
        'italian': 'it-IT',
        'portuguese': 'pt-PT',
        'russian': 'ru-RU',
    };

    function detectVoiceTranslationCommand(text) {
        if (!text) return null;
        const cleaned = text.trim().replace(/[.!?,;:]+$/, '');
        for (const pattern of VOICE_TRANSLATE_PATTERNS) {
            const match = cleaned.match(pattern);
            if (match && match[1]) {
                const raw = match[1].trim().toLowerCase();
                return CANONICAL_LANG_NAMES[raw] || (raw.charAt(0).toUpperCase() + raw.slice(1));
            }
        }
        return null;
    }

    function showTranslationOffer() {
        if (translationOfferBox) {
            translationOfferBox.style.display = 'flex';
        }
    }

    function hideTranslationOffer() {
        if (translationOfferBox) {
            translationOfferBox.style.display = 'none';
        }
    }

    function showTranslationSelector() {
        if (translationSelectorBox) {
            translationSelectorBox.style.display = 'flex';
            hideTranslationError();
            if (lastSourceLanguage && lastSourceLanguage.toLowerCase() === 'hi') {
                targetLanguageSelect.value = 'English';
            }
            translationSelectorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function hideTranslationSelector() {
        if (translationSelectorBox) {
            translationSelectorBox.style.display = 'none';
            hideTranslationError();
        }
    }

    function showTranslationResult() {
        if (translationDisplayCard) {
            translationDisplayCard.style.display = 'flex';
        }
    }

    function hideTranslationResult() {
        if (translationDisplayCard) {
            translationDisplayCard.style.display = 'none';
        }
        stopSpeechSynthesis();
    }

    function showTranslationError(msg) {
        if (translationErrorNotice && translationErrorMsg) {
            translationErrorMsg.textContent = msg || "Translation couldn't be completed.";
            translationErrorNotice.style.display = 'flex';
        }
        showToast(msg || "Translation couldn't be completed.");
    }

    function hideTranslationError() {
        if (translationErrorNotice) {
            translationErrorNotice.style.display = 'none';
        }
    }

    function setTranslationControlsBusy(busy) {
        if (btnTriggerTranslate) {
            btnTriggerTranslate.disabled = busy;
            triggerTranslateText.textContent = busy ? 'Translating...' : 'Translate';
        }
    }

    async function executeTranslation(sourceText, targetLang, sourceLang = null) {
        if (!sourceText || !sourceText.trim()) {
            showError('Please record something first.', 'There is no transcription available to translate.');
            showToast('Please record something first.');
            return;
        }

        lastAttemptedTargetLanguage = targetLang;
        hideTranslationError();
        showStatus(`Translating to ${targetLang}...`);
        setTranslationControlsBusy(true);

        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: sourceText.trim(),
                    target_language: targetLang,
                    source_language: sourceLang || lastSourceLanguage,
                }),
            });

            const data = await response.json();
            hideStatus();
            setTranslationControlsBusy(false);

            if (response.ok && data.status === 'success') {
                currentTranslationData = {
                    sourceText: data.source_text,
                    translatedText: data.translated_text,
                    targetLanguage: data.target_language || targetLang,
                    sourceLanguage: data.source_language || (sourceLang ? sourceLang.toUpperCase() : 'Original'),
                };

                renderTranslationResult(currentTranslationData);
                hideTranslationOffer();
                hideTranslationSelector();
                showToast(`Translated to ${currentTranslationData.targetLanguage}`);

                translationDisplayCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                const errorText = data.error || "Translation couldn't be completed.";
                showTranslationError(errorText);
            }
        } catch (err) {
            console.error('Translation network error:', err);
            hideStatus();
            setTranslationControlsBusy(false);
            showTranslationError("Translation couldn't be completed.");
        }
    }

    function renderTranslationResult(data) {
        const srcDisplay = data.sourceLanguage ? data.sourceLanguage.toUpperCase() : 'ORIGINAL';
        translationRouteText.textContent = `${srcDisplay} → ${data.targetLanguage}`;

        // Never replace the original transcription; always show both
        transOriginalContent.textContent = data.sourceText;
        transTargetTitle.textContent = `Translation — ${data.targetLanguage}`;
        transTargetContent.textContent = data.translatedText;

        showTranslationResult();
    }

    function copyTranslation() {
        if (!currentTranslationData || !currentTranslationData.translatedText) return;
        const text = currentTranslationData.translatedText;

        navigator.clipboard.writeText(text).then(() => {
            copyTranslationBtnText.textContent = 'Copied';
            showToast('Translation copied to clipboard.');
            setTimeout(() => {
                copyTranslationBtnText.textContent = 'Copy';
            }, 1800);
        }).catch(() => {
            showToast('Failed to copy translation.');
        });
    }

    function downloadTranslation() {
        if (!currentTranslationData) return;
        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const hh = String(now.getHours()).padStart(2, '0');
        const min = String(now.getMinutes()).padStart(2, '0');
        const ss = String(now.getSeconds()).padStart(2, '0');

        const content = [
            `============================================================`,
            `Speech Recognition Studio — Translation Record`,
            `Date: ${now.toLocaleString()}`,
            `Route: ${currentTranslationData.sourceLanguage} → ${currentTranslationData.targetLanguage}`,
            `============================================================\n`,
            `### Original (${currentTranslationData.sourceLanguage})`,
            currentTranslationData.sourceText,
            `\n### Translation — ${currentTranslationData.targetLanguage}`,
            currentTranslationData.translatedText,
            `\n============================================================`
        ].join('\n');

        const filename = `translation_${currentTranslationData.targetLanguage.toLowerCase()}_${yyyy}${mm}${dd}_${hh}${min}${ss}.txt`;

        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast(`Downloaded: ${filename}`);
    }

    function listenTranslation() {
        if (!currentTranslationData || !currentTranslationData.translatedText) return;

        if (!('speechSynthesis' in window)) {
            showToast('Text-to-speech is not supported by your browser.');
            return;
        }

        if (isSpeaking) {
            stopSpeechSynthesis();
            return;
        }

        stopSpeechSynthesis();

        const utterance = new SpeechSynthesisUtterance(currentTranslationData.translatedText);
        const targetLower = currentTranslationData.targetLanguage.toLowerCase();
        const langCode = TTS_LANG_MAP[targetLower] || 'en-US';
        utterance.lang = langCode;

        utterance.onstart = () => {
            isSpeaking = true;
            listenTranslationBtnText.textContent = 'Stop';
        };

        utterance.onend = () => {
            isSpeaking = false;
            listenTranslationBtnText.textContent = 'Listen';
        };

        utterance.onerror = () => {
            isSpeaking = false;
            listenTranslationBtnText.textContent = 'Listen';
        };

        window.speechSynthesis.speak(utterance);
    }

    function stopSpeechSynthesis() {
        if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }
        isSpeaking = false;
        if (listenTranslationBtnText) {
            listenTranslationBtnText.textContent = 'Listen';
        }
    }

    // =========================================================================
    // 11. EVENT LISTENERS
    // =========================================================================
    function setupEventListeners() {
        // Navigation Buttons
        btnScrollHistory.addEventListener('click', () => {
            historySection.scrollIntoView({ behavior: 'smooth' });
        });

        btnResetWorkspace.addEventListener('click', resetWorkspace);
        btnCloseError.addEventListener('click', hideError);

        // Recording Controls
        btnStartRecord.addEventListener('click', startRecording);
        btnStopRecord.addEventListener('click', stopRecording);
        btnCancelRecord.addEventListener('click', cancelRecording);

        // Upload Dropzone
        dropzone.addEventListener('click', () => {
            fileInput.click();
        });

        dropzone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInput.click();
            }
        });

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-active');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('drag-active');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-active');
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });

        btnRemoveFile.addEventListener('click', removeSelectedFile);

        btnTranscribeFile.addEventListener('click', () => {
            if (selectedUploadFile) {
                sendAudioToTranscribe(selectedUploadFile, selectedUploadFile.name);
            }
        });

        // Transcript Action Buttons
        btnCopyTranscript.addEventListener('click', copyTranscript);
        btnDownloadTranscript.addEventListener('click', downloadTranscript);
        btnClearTranscript.addEventListener('click', clearTranscript);

        // Translation Offer actions
        btnOfferTranslate.addEventListener('click', () => {
            hideTranslationOffer();
            showTranslationSelector();
        });

        btnOfferSkip.addEventListener('click', () => {
            hideTranslationOffer();
        });

        // Translation Selector actions
        btnCloseSelector.addEventListener('click', () => {
            hideTranslationSelector();
        });

        targetLanguageSelect.addEventListener('change', () => {
            if (targetLanguageSelect.value === '__other__') {
                otherLanguageWrapper.style.display = 'block';
                otherLanguageInput.focus();
            } else {
                otherLanguageWrapper.style.display = 'none';
            }
        });

        btnTriggerTranslate.addEventListener('click', () => {
            let targetLang = targetLanguageSelect.value;
            if (targetLang === '__other__') {
                targetLang = otherLanguageInput.value.trim();
                if (!targetLang) {
                    showTranslationError('Please enter a target language.');
                    return;
                }
            }
            if (!targetLang) {
                showTranslationError('Please choose a target language.');
                return;
            }
            const sourceText = (transcriptText.value || lastTranscription || '').trim();
            executeTranslation(sourceText, targetLang, lastSourceLanguage);
        });

        otherLanguageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                btnTriggerTranslate.click();
            }
        });

        btnRetryTranslate.addEventListener('click', () => {
            const sourceText = (transcriptText.value || lastTranscription || '').trim();
            executeTranslation(sourceText, lastAttemptedTargetLanguage, lastSourceLanguage);
        });

        // Translation Display Actions
        btnCopyTranslation.addEventListener('click', copyTranslation);
        btnDownloadTranslation.addEventListener('click', downloadTranslation);
        btnListenTranslation.addEventListener('click', listenTranslation);

        btnRetranslate.addEventListener('click', () => {
            showTranslationSelector();
        });

        // History Actions
        btnClearHistory.addEventListener('click', clearAllHistory);
    }

    // Initialize application
    init();
});
