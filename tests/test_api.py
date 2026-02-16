import pytest
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)

def test_start_scan():
    response = client.post("/api/scans", json={"target": "example.com"})
    assert response.status_code == 200
    assert "scan_id" in response.json()
