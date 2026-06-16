/**
 * Voice Assistant — Frontend Logic
 * ==================================
 * Handles:
 *  - Microphone recording via MediaRecorder API
 *  - File upload (wav, mp3, webm, ogg, flac, m4a)
 *  - Sending audio to /transcribe
 *  - Rendering conversation-style messages
 *  - Waveform visualisation during recording
 *  - Confirmation flow for dangerous commands
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM References ---
    const chatArea         = document.getElementById('chat-area');
    const micBtn           = document.getElementById('mic-btn');
    const fileInput        = document.getElementById('file-input');
    const uploadLabel      = document.getElementById('upload-label');
    const inputHint        = document.getElementById('input-hint');
    const recordingTimer   = document.getElementById('recording-timer');
    const statusIndicator  = document.getElementById('status-indicator');
    const statusText       = document.getElementById('status-text');
    const waveformContainer = document.getElementById('waveform-container');
    const waveformCanvas   = document.getElementById('waveform-canvas');

    // Confirmation modal
    const confirmModal     = document.getElementById('confirm-modal');
    const confirmMessage   = document.getElementById('confirm-message');
    const confirmExecute   = document.getElementById('confirm-execute');
    const confirmCancel    = document.getElementById('confirm-cancel');

    let mediaRecorder      = null;
    let audioChunks        = [];
    let isRecording        = false;
    let recordingStartTime = null;
    let timerInterval      = null;
    let audioContext        = null;
    let analyser            = null;
    let animationFrameId    = null;

    // Pending confirmation token
    let pendingToken       = null;


    // =========================================================================
    // UTILITY: Create message elements
    // =========================================================================
    function createAssistantAvatar() {
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3Z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
        `;
        return avatar;
    }

    function createUserAvatar() {
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = 'You';
        return avatar;
    }

    function addUserMessage(text) {
        const msg = document.createElement('div');
        msg.className = 'message user-message';

        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = `<p class="transcription-text">"${escapeHtml(text)}"</p>`;

        msg.appendChild(content);
        msg.appendChild(createUserAvatar());
        chatArea.appendChild(msg);
        scrollToBottom();
    }

    function addAssistantMessage(html) {
        const msg = document.createElement('div');
        msg.className = 'message assistant-message';

        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = html;

        msg.appendChild(createAssistantAvatar());
        msg.appendChild(content);
        chatArea.appendChild(msg);
        scrollToBottom();
        return content;
    }

    function addLoadingMessage() {
        const msg = document.createElement('div');
        msg.className = 'message assistant-message';
        msg.id = 'loading-message';

        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = `
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        `;

        msg.appendChild(createAssistantAvatar());
        msg.appendChild(content);
        chatArea.appendChild(msg);
        scrollToBottom();
    }

    function removeLoadingMessage() {
        const el = document.getElementById('loading-message');
        if (el) el.remove();
    }

    function addErrorMessage(text) {
        addAssistantMessage(`
            <p class="error-content">
                <span class="error-icon">⚠️</span>
                ${escapeHtml(text)}
            </p>
        `);
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatArea.scrollTop = chatArea.scrollHeight;
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function setStatus(state, text) {
        statusIndicator.className = 'status-indicator ' + state;
        statusText.textContent = text;
    }

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }


    // =========================================================================
    // WAVEFORM VISUALIZER
    // =========================================================================
    function startWaveform(stream) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        const ctx = waveformCanvas.getContext('2d');

        waveformContainer.style.display = 'block';

        function draw() {
            animationFrameId = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);

            const w = waveformCanvas.width;
            const h = waveformCanvas.height;
            ctx.clearRect(0, 0, w, h);

            const barWidth = (w / bufferLength) * 2.5;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * h * 0.9;

                const gradient = ctx.createLinearGradient(0, h, 0, h - barHeight);
                gradient.addColorStop(0, 'rgba(99, 102, 241, 0.6)');
                gradient.addColorStop(1, 'rgba(139, 92, 246, 0.9)');

                ctx.fillStyle = gradient;
                ctx.fillRect(x, h - barHeight, barWidth - 1, barHeight);
                x += barWidth + 1;
            }
        }

        draw();
    }

    function stopWaveform() {
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }
        waveformContainer.style.display = 'none';
    }


    // =========================================================================
    // MICROPHONE RECORDING
    // =========================================================================
    micBtn.addEventListener('click', async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

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
                    const audioFile = new File([audioBlob], 'recording.webm', { type: mimeType });

                    // Release microphone
                    stream.getTracks().forEach(track => track.stop());
                    stopWaveform();

                    // Send to server
                    sendAudio(audioFile);
                };

                mediaRecorder.start();
                isRecording = true;
                micBtn.classList.add('recording');
                setStatus('recording', 'Recording…');
                inputHint.textContent = 'Tap again to stop recording';

                // Start timer
                recordingStartTime = Date.now();
                recordingTimer.style.display = 'inline';
                timerInterval = setInterval(() => {
                    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                    recordingTimer.textContent = formatTime(elapsed);
                }, 1000);

                // Start waveform
                startWaveform(stream);

            } catch (err) {
                console.error('Microphone access error:', err);
                addErrorMessage('Microphone access denied or unavailable. Please check browser permissions.');
            }
        } else {
            // Stop recording
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            isRecording = false;
            micBtn.classList.remove('recording');
            recordingTimer.style.display = 'none';
            clearInterval(timerInterval);
            inputHint.textContent = 'Tap the microphone to start recording';
        }
    });


    // =========================================================================
    // FILE UPLOAD
    // =========================================================================
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            sendAudio(file);
            fileInput.value = '';  // Reset so same file can be re-uploaded
        }
    });


    // =========================================================================
    // SEND AUDIO TO SERVER
    // =========================================================================
    async function sendAudio(audioFile) {
        addUserMessage(`🎤 Audio: ${audioFile.name}`);
        addLoadingMessage();
        setStatus('processing', 'Transcribing…');
        inputHint.textContent = 'Processing your audio…';

        const formData = new FormData();
        formData.append('audio', audioFile);

        try {
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData,
            });

            let data;
            try {
                data = await response.json();
            } catch (_) {
                throw new Error('Invalid response from server.');
            }

            removeLoadingMessage();

            if (data.status === 'success') {
                renderSuccessResponse(data);
            } else {
                addErrorMessage(data.error || 'An unknown error occurred.');
            }
        } catch (err) {
            console.error('Request error:', err);
            removeLoadingMessage();
            addErrorMessage(err.message || 'Could not connect to the server.');
        }

        setStatus('', 'Ready');
        inputHint.textContent = 'Tap the microphone to start recording';
    }


    // =========================================================================
    // RENDER RESPONSE
    // =========================================================================
    function renderSuccessResponse(data) {
        let html = '';

        // Transcription
        if (data.transcription) {
            html += `<p class="transcription-text">"${escapeHtml(data.transcription)}"</p>`;
        }

        // Command result
        if (data.command) {
            const cmd = data.command;

            if (cmd.requires_confirmation) {
                // Dangerous command — needs confirmation
                const cardClass = 'warning';
                html += `
                    <div class="command-card ${cardClass}">
                        <div class="command-label">⚠️ Dangerous Command Detected</div>
                        <div class="command-intent">${escapeHtml(cmd.intent || '')}</div>
                        ${cmd.action ? `<div class="command-action">${escapeHtml(cmd.action)}</div>` : ''}
                        <div class="command-output">${escapeHtml(cmd.warning || '')}</div>
                        <button class="inline-confirm-btn" data-token="${escapeHtml(cmd.confirmation_token)}">
                            ⚡ Confirm & Execute
                        </button>
                        <button class="inline-cancel-btn" data-token-cancel="true">
                            Cancel
                        </button>
                    </div>
                `;
            } else {
                // Normal command result
                const cardClass = cmd.executed ? 'executed' : 'error';
                html += `
                    <div class="command-card ${cardClass}">
                        <div class="command-label">${cmd.executed ? '✅ Command Executed' : '❌ Command Failed'}</div>
                        <div class="command-intent">${escapeHtml(cmd.intent || '')}</div>
                        ${cmd.action ? `<div class="command-action">${escapeHtml(String(cmd.action))}</div>` : ''}
                        <div class="command-output">${escapeHtml(cmd.output || '')}</div>
                    </div>
                `;
            }
        } else if (data.transcription) {
            // No command detected — just transcription
            html += `
                <div class="command-card">
                    <div class="command-label">No command detected</div>
                    <div class="command-output">Transcription returned only. No matching system command was found.</div>
                </div>
            `;
        }

        const content = addAssistantMessage(html);

        // Attach event listeners for inline confirm/cancel buttons
        const confirmBtn = content.querySelector('.inline-confirm-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                const token = confirmBtn.dataset.token;
                executeConfirmedCommand(token, content);
            });
        }

        const cancelBtn = content.querySelector('.inline-cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                // Replace the card with "cancelled" message
                const card = content.querySelector('.command-card.warning');
                if (card) {
                    card.className = 'command-card';
                    card.innerHTML = `
                        <div class="command-label">🚫 Cancelled</div>
                        <div class="command-output">The dangerous command was not executed.</div>
                    `;
                }
            });
        }
    }


    // =========================================================================
    // EXECUTE CONFIRMED DANGEROUS COMMAND
    // =========================================================================
    async function executeConfirmedCommand(token, contentEl) {
        // Disable buttons
        const confirmBtn = contentEl.querySelector('.inline-confirm-btn');
        const cancelBtn = contentEl.querySelector('.inline-cancel-btn');
        if (confirmBtn) confirmBtn.disabled = true;
        if (cancelBtn) cancelBtn.disabled = true;

        setStatus('processing', 'Executing…');

        try {
            const response = await fetch('/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    confirmation_token: token,
                    confirmed: true,
                }),
            });

            const data = await response.json();

            // Update the card in-place
            const card = contentEl.querySelector('.command-card.warning');
            if (card && data.command) {
                const cmd = data.command;
                card.className = 'command-card ' + (cmd.executed ? 'executed' : 'error');
                card.innerHTML = `
                    <div class="command-label">${cmd.executed ? '✅ Command Executed' : '❌ Execution Failed'}</div>
                    <div class="command-intent">${escapeHtml(cmd.intent || '')}</div>
                    ${cmd.action ? `<div class="command-action">${escapeHtml(String(cmd.action))}</div>` : ''}
                    <div class="command-output">${escapeHtml(cmd.output || '')}</div>
                `;
            } else if (data.error) {
                addErrorMessage(data.error);
            }
        } catch (err) {
            addErrorMessage('Failed to execute command: ' + err.message);
        }

        setStatus('', 'Ready');
    }


    // =========================================================================
    // MODAL (kept for potential future use, but inline confirm is primary)
    // =========================================================================
    confirmCancel.addEventListener('click', () => {
        confirmModal.style.display = 'none';
        pendingToken = null;
    });

    confirmExecute.addEventListener('click', async () => {
        confirmModal.style.display = 'none';
        if (pendingToken) {
            // Using modal flow (backup)
            addLoadingMessage();
            setStatus('processing', 'Executing…');
            try {
                const response = await fetch('/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        confirmation_token: pendingToken,
                        confirmed: true,
                    }),
                });
                const data = await response.json();
                removeLoadingMessage();
                if (data.command) {
                    const cmd = data.command;
                    const cardClass = cmd.executed ? 'executed' : 'error';
                    addAssistantMessage(`
                        <div class="command-card ${cardClass}">
                            <div class="command-label">${cmd.executed ? '✅ Command Executed' : '❌ Execution Failed'}</div>
                            <div class="command-intent">${escapeHtml(cmd.intent || '')}</div>
                            ${cmd.action ? `<div class="command-action">${escapeHtml(String(cmd.action))}</div>` : ''}
                            <div class="command-output">${escapeHtml(cmd.output || '')}</div>
                        </div>
                    `);
                }
            } catch (err) {
                removeLoadingMessage();
                addErrorMessage('Failed to execute command: ' + err.message);
            }
            setStatus('', 'Ready');
            pendingToken = null;
        }
    });


    // =========================================================================
    // HINT CHIPS — Quick command demos
    // =========================================================================
    document.querySelectorAll('.hint-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            // For hint chips, we just display what would happen.
            // In a real scenario the user would speak these.
            const hint = chip.dataset.hint;
            addAssistantMessage(`
                <p style="color: var(--text-secondary); font-size: 0.875rem;">
                    💡 Try saying: <strong>"${escapeHtml(hint)}"</strong>
                </p>
                <p style="color: var(--text-muted); font-size: 0.8rem; margin-top: 4px;">
                    Use the microphone to speak this command.
                </p>
            `);
        });
    });
});
