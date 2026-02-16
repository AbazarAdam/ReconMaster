# ReconMaster: API Reference

ReconMaster features a RESTful API powered by FastAPI, allowing for programmatic control over scan operations and data retrieval.

## 🔑 Authentication
*Note: Current version does not enforce authentication. For production, please implement an API Key or OAuth2 layer.*

## 📌 Endpoint Summary

| Component | Endpoint | Method | Description |
| :--- | :--- | :--- | :--- |
| **Scans** | `/api/scans` | `GET` | List all previous scan sessions. |
| **Scans** | `/api/scans` | `POST` | Initialize a new scan for a target. |
| **Scans** | `/api/scans/{id}` | `GET` | Retrieve metadata for a specific scan. |
| **Scans** | `/api/scans/{id}` | `DELETE` | Cancel or remove a scan session. |
| **Results** | `/api/scans/{id}/results` | `GET` | Retrieve findings associated with a scan. |
| **Targets** | `/api/targets/{target}/results` | `GET` | Retrieve all historical findings for a target. |

---

## 🚀 Scan Management

### Start a Scan
`POST /api/scans`

**Request Body:**
```json
{
  "target": "example.com"
}
```

**Response (202 Accepted):**
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running"
}
```

---

## 📊 Result Models

### Subdomain Finding
```json
{
  "type": "subdomain",
  "data": {
    "subdomain": "api.example.com",
    "source": "virustotal"
  }
}
```

### HTTP Service Finding
```json
{
  "type": "http",
  "data": {
    "url": "https://api.example.com",
    "status": 200,
    "title": "API Gateway",
    "server": "nginx"
  }
}
```

---

## 🔌 WebSocket Integration

**Endpoint**: `/ws/{scan_id}`

The dashboard uses this endpoint to stream live logs and progress updates in JSON format.

**Message Format:**
```json
{
  "type": "log",
  "message": "Starting Shodan enrichment phase..."
}
```

---
For implementation details of the web server, refer to `web/app.py` and `web/api.py`.
