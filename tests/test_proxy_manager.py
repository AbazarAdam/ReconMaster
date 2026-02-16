from core.proxy_manager import ProxyManager

import asyncio

def test_proxy_manager_connector():
    config = {"http": "http://127.0.0.1:8080"}
    pm = ProxyManager(config)
    async def get_conn():
        return pm.get_connector()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    connector = loop.run_until_complete(get_conn())
    assert connector is not None
    loop.close()
