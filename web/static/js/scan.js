
// scan.js: Handles live scan progress via WebSocket
function getScanIdFromUrl() {
	const match = window.location.pathname.match(/\/scan\/([\w-]+)/);
	return match ? match[1] : null;
}

function updateProgress(status, progress, target) {
	document.getElementById('scan-meta').textContent = `Target: ${target} | Status: ${status}`;
	const bar = document.getElementById('scan-progress-bar');
	bar.style.width = progress + '%';
	bar.textContent = progress + '%';
	if (progress >= 100) {
		document.getElementById('view-results-btn').style.display = '';
	}
}

window.addEventListener('DOMContentLoaded', () => {
	const scanId = getScanIdFromUrl();
	if (!scanId) return;
	const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
	const ws = new WebSocket(`${wsProto}://${window.location.host}/ws/${scanId}`);
	ws.onmessage = (event) => {
		const msg = JSON.parse(event.data);
		if (msg.type === 'progress') {
			updateProgress(msg.status, msg.progress, msg.target);
		}
	};
	ws.onclose = () => {
		const log = document.getElementById('scan-log');
		log.textContent += '\n[WebSocket closed]';
	};
});
