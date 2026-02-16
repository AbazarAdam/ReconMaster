// index.js: Handles scan form and scan list

document.getElementById('scan-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const target = document.getElementById('target').value;
    const res = await fetch('/api/scans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target })
    });
    const data = await res.json();
    if (data.scan_id) {
        window.location.href = `/scan/${data.scan_id}`;
    }
});


// Load and display list of scans
async function loadScans() {
    const res = await fetch('/api/scans');
    const scans = await res.json();
    const tbody = document.getElementById('scans-list');
    tbody.innerHTML = '';
    for (const scan of scans) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${scan.target}</td>
            <td>-</td>
            <td>${scan.status}</td>
            <td><a href="/scan/${scan.scan_id}" class="btn btn-sm btn-neon">View</a></td>
        `;
        tbody.appendChild(tr);
    }
}

window.addEventListener('DOMContentLoaded', loadScans);
