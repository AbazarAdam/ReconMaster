import pytest
from unittest.mock import AsyncMock, patch

from modules.subdomain import ct
from core.module_loader import BaseModule

@pytest.mark.asyncio
@patch("modules.subdomain.ct.aiohttp.ClientSession.get")
async def test_ct_module_fetch(mock_get):
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=[{"name_value": "a.example.com"}])
    mock_get.return_value.__aenter__.return_value = mock_resp
    # Mock dependencies for BaseModule
    class DummyDB:
        def store_result(self, *args, **kwargs):
            self.stored = True
    dummy_db = DummyDB()
    module = ct.CertificateTransparency({}, dummy_db)
    await module.run("example.com")
    # No exception means pass; optionally check dummy_db.stored
    assert hasattr(dummy_db, "stored")
