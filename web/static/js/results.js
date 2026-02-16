document.addEventListener("DOMContentLoaded", function () {
    if (!window.TARGET) return;

    fetchResults();

    // Filter logic for subdomains
    document.getElementById("searchSubdomains").addEventListener("keyup", function () {
        const filter = this.value.toLowerCase();
        const rows = document.querySelectorAll("#tableSubdomains tbody tr");
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filter) ? "" : "none";
        });
    });
});

async function fetchResults() {
    try {
        const target = window.TARGET;
        const scanId = window.SCAN_ID;
        let url;

        if (scanId) {
            console.log(`[DEBUG] Fetching results for scan: ${scanId}`);
            url = `/api/scans/${scanId}/results`;
        } else {
            console.log(`[DEBUG] No scan ID, fetching all results for target: ${target}`);
            url = `/api/targets/${target}/results`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch results");

        const results = await response.json();
        console.log(`[DEBUG] Received ${results.length} results`);
        processResults(results);
    } catch (e) {
        console.error(e);
        // Show error in summary
        document.getElementById("summaryStats").innerHTML = `<div class="alert alert-danger w-100">Failed to load results: ${e.message}</div>`;
    }
}

function processResults(results) {
    const data = {
        subdomains: [],
        ports: [],
        http: [],
        screenshots: []
    };

    results.forEach(res => {
        const type = res.type;
        const item = res.data;

        // "item" might be a list (common for subdomain modules) or a dict
        const items = Array.isArray(item) ? item : [item];

        items.forEach(entry => {
            if (type === 'subdomain') data.subdomains.push({ ...entry, source: res.module });
            else if (type === 'portscan' || type === 'port') data.ports.push({ ...entry, source: res.module });
            else if (type === 'http') data.http.push({ ...entry, source: res.module });
            else if (type === 'screenshot') data.screenshots.push({ ...entry, source: res.module });
        });
    });

    // Deduplicate logic simpler done in backend, but basic rendering here:
    renderSubdomains(data.subdomains);
    renderPorts(data.ports);
    renderHttp(data.http);
    renderScreenshots(data.screenshots);

    // Update counts
    document.getElementById("count-subdomains").innerText = data.subdomains.length;
    document.getElementById("count-ports").innerText = data.ports.length;
    document.getElementById("count-http").innerText = data.http.length;
}

function renderSubdomains(items) {
    const tbody = document.querySelector("#tableSubdomains tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    // Simple dedup by subdomain name
    const unique = {};
    items.forEach(i => {
        if (i.subdomain) unique[i.subdomain] = i;
    });

    Object.values(unique).forEach(item => {
        const row = `<tr>
            <td class="text-neon-cyan">${item.subdomain}</td>
            <td>${item.source || 'N/A'}</td>
            <td>${item.ip || 'N/A'}</td>
        </tr>`;
        tbody.innerHTML += row;
    });
}

function renderPorts(items) {
    const tbody = document.querySelector("#tablePorts tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    items.forEach(item => {
        const row = `<tr>
            <td>${item.ip || item.host || window.TARGET || 'N/A'}</td>
            <td><span class="badge bg-danger">${item.port}</span></td>
            <td>${item.service || 'unknown'}</td>
            <td>${item.state || 'open'}</td>
        </tr>`;
        tbody.innerHTML += row;
    });
}

function renderHttp(items) {
    const tbody = document.querySelector("#tableHttp tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    items.forEach(item => {
        const row = `<tr>
            <td><a href="${item.url}" target="_blank" class="text-light">${item.url}</a></td>
            <td><span class="badge bg-${item.status < 400 ? 'success' : 'danger'}">${item.status}</span></td>
            <td>${item.title || ''}</td>
            <td>${(item.technologies || []).join(", ")}</td>
        </tr>`;
        tbody.innerHTML += row;
    });
}

function renderScreenshots(items) {
    const gallery = document.getElementById("galleryScreenshots");
    if (!gallery) return;
    gallery.innerHTML = "";
    if (items.length === 0) {
        gallery.innerHTML = '<div class="col-12 text-center text-muted">No screenshots captured for this scan.</div>';
        return;
    }

    items.forEach(item => {
        // Backend uses 'screenshot_path', frontend was using 'path'
        let src = item.screenshot_path || item.path;
        if (src && !src.startsWith("http")) {
            // Basic naive adjustment
            src = "/" + src.replace(/\\/g, "/");
        }

        const col = document.createElement("div");
        col.className = "col-md-3 mb-4";
        col.innerHTML = `
            <div class="card bg-dark border-secondary h-100">
                <img src="${src}" class="card-img-top" alt="Screenshot" 
                     style="cursor: pointer; height: 200px; object-fit: cover;"
                     onclick="openLightbox('${src}', '${item.url || 'Screenshot'}')">
                <div class="card-body p-2">
                    <small class="text-muted text-truncate d-block">${item.url}</small>
                </div>
            </div>
        `;
        gallery.appendChild(col);
    });
}

function openLightbox(src, title) {
    const img = document.getElementById("lightboxImage");
    const t = document.getElementById("lightboxTitle");
    if (img) img.src = src;
    if (t) t.innerText = title;
    new bootstrap.Modal(document.getElementById("lightboxModal")).show();
}
