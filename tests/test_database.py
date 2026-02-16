import pytest
import asyncio
from core import database

def test_store_and_retrieve_results(tmp_path):
    db_path = tmp_path / "test.db"
    db = database.Database(str(db_path))
    target = "example.com"
    module = "subdomain/ct"
    source = "ct"
    result_type = "subdomain"
    data = {"subdomain": "test.example.com", "source": "ct"}
    db.store_result(target, module, source, result_type, data)
    results = db.get_results(target, module)
    found = False
    for r in results:
        d = r["data"]
        if isinstance(d, dict) and d.get("subdomain") == "test.example.com":
            found = True
    assert found
