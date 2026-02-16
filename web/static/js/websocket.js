// WebSocket client for live scan updates
// Version: 6 - Complete rewrite with robust error handling

(function () {
    'use strict';

    console.log('[WebSocket] Script loaded');

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWebSocket);
    } else {
        initWebSocket();
    }

    function initWebSocket() {
        console.log('[WebSocket] Initializing...');

        // Check if SCAN_ID is defined
        if (typeof window.SCAN_ID === 'undefined' || !window.SCAN_ID) {
            console.warn('[WebSocket] No SCAN_ID defined, skipping WebSocket connection');
            return;
        }

        console.log('[WebSocket] SCAN_ID:', window.SCAN_ID);

        // Get DOM elements
        const logConsole = document.getElementById('logConsole');
        const scanStatus = document.getElementById('scanStatus');
        const btnResults = document.getElementById('btnViewResults');
        const scanProgress = document.getElementById('scanProgress');

        if (!logConsole) {
            console.error('[WebSocket] logConsole element not found!');
            return;
        }

        console.log('[WebSocket] DOM elements found:', {
            logConsole: !!logConsole,
            scanStatus: !!scanStatus,
            btnResults: !!btnResults,
            scanProgress: !!scanProgress
        });

        // Build WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${window.SCAN_ID}`;

        console.log('[WebSocket] Connecting to:', wsUrl);

        // Create WebSocket connection
        let ws;
        try {
            ws = new WebSocket(wsUrl);
        } catch (error) {
            console.error('[WebSocket] Failed to create WebSocket:', error);
            addLog(logConsole, '[ERROR] Failed to create WebSocket connection', 'text-danger');
            return;
        }

        // Helper function to add log entry
        function addLog(container, message, className = '') {
            const div = document.createElement('div');
            if (className) {
                div.className = className;
            }
            div.textContent = message;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
            console.log('[WebSocket] Log added:', message);
        }

        // WebSocket event handlers
        ws.onopen = function () {
            console.log('[WebSocket] Connection opened');
            addLog(logConsole, '[System] Connected to live updates...', 'text-success');
        };

        ws.onmessage = function (event) {
            console.log('[WebSocket] Message received:', event.data);

            let data;
            try {
                data = JSON.parse(event.data);
            } catch (error) {
                console.error('[WebSocket] Failed to parse message:', error);
                addLog(logConsole, '[ERROR] Invalid message format', 'text-danger');
                return;
            }

            console.log('[WebSocket] Parsed data:', data);

            const msgType = data.type;

            // Handle different message types
            if (msgType === 'log') {
                const timestamp = new Date().toLocaleTimeString();
                const message = data.message || '';
                addLog(logConsole, `[${timestamp}] ${message}`);

            } else if (msgType === 'status') {
                const status = data.status;
                console.log('[WebSocket] Status update:', status);

                if (scanStatus) {
                    scanStatus.textContent = status.toUpperCase();
                    scanStatus.classList.remove('status-pending', 'status-running', 'status-completed', 'status-failed');
                    scanStatus.classList.add(`status-${status}`);
                }

                if (status === 'completed') {
                    addLog(logConsole, '[System] Scan Completed!', 'text-success fw-bold');
                    if (btnResults) {
                        btnResults.classList.remove('disabled');
                    }
                    if (scanProgress) {
                        scanProgress.style.width = '100%';
                    }
                } else if (status === 'failed') {
                    addLog(logConsole, '[System] Scan Failed', 'text-danger fw-bold');
                    if (scanProgress) {
                        scanProgress.classList.add('bg-danger');
                    }
                }

            } else if (msgType === 'phase') {
                const phase = data.phase || 'Unknown Phase';
                console.log('[WebSocket] Phase update:', phase);
                addLog(logConsole, `>>> ${phase}`, 'text-info fw-bold');

                // Update progress bar based on phase
                if (scanProgress) {
                    let width = '0%';
                    if (phase.includes('Phase 1')) width = '20%';
                    else if (phase.includes('Phase 2')) width = '40%';
                    else if (phase.includes('Phase 3')) width = '60%';
                    else if (phase.includes('Phase 4')) width = '80%';
                    else if (phase.includes('Phase 5')) width = '95%';
                    scanProgress.style.width = width;
                }

            } else if (msgType === 'error') {
                const errorMsg = data.message || 'Unknown error';
                console.error('[WebSocket] Error message:', errorMsg);
                addLog(logConsole, `[ERROR] ${errorMsg}`, 'text-danger');

            } else {
                console.warn('[WebSocket] Unknown message type:', msgType, data);
                addLog(logConsole, `[${msgType}] ${JSON.stringify(data)}`, 'text-muted');
            }
        };

        ws.onerror = function (error) {
            console.error('[WebSocket] Error:', error);
            addLog(logConsole, '[ERROR] WebSocket connection error', 'text-danger');
        };

        ws.onclose = function (event) {
            console.log('[WebSocket] Connection closed:', event.code, event.reason);
            addLog(logConsole, '[System] Connection closed', 'text-muted');
        };

        // Store WebSocket reference globally for debugging
        window.debugWebSocket = ws;
        console.log('[WebSocket] Initialization complete. WebSocket available as window.debugWebSocket');
    }
})();
