import asyncio
import aiohttp
import json

async def test_backend():
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # 1. Test Homepage
        try:
            async with session.get(base_url) as resp:
                print(f"GET / status: {resp.status}")
                if resp.status == 200:
                    text = await resp.text()
                    if "ReconMaster" in text:
                        print("✅ Homepage loaded successfully")
                    else:
                        print("❌ Homepage loaded but missing content")
                else:
                    print("❌ Homepage failed")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return

        # 2. Start Scan
        scan_id = None
        try:
            payload = {"target": "scanme.nmap.org"}
            async with session.post(f"{base_url}/api/scans", json=payload) as resp:
                print(f"POST /api/scans status: {resp.status}")
                if resp.status == 201:
                    data = await resp.json()
                    scan_id = data.get("scan_id")
                    print(f"✅ Scan started with ID: {scan_id}")
                else:
                    text = await resp.text()
                    print(f"❌ Failed to start scan: {text}")
                    return
        except Exception as e:
            print(f"❌ Scan start failed: {e}")
            return

        # 3. Test WebSocket
        if scan_id:
            ws_url = f"ws://localhost:8000/ws/{scan_id}"
            try:
                async with session.ws_connect(ws_url) as ws:
                    print(f"✅ Connected to WebSocket: {ws_url}")
                    # Wait for a few messages
                    count = 0
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            print(f"📩 Received WS message type: {data.get('type')}")
                            if data.get('type') == 'status' and data.get('status') == 'completed':
                                print("✅ Scan completed successfully")
                                break
                            count += 1
                            if count >= 3:
                                print("✅ Received initial progress updates")
                                break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print("❌ WebSocket connection closed with error")
                            break
            except Exception as e:
                print(f"❌ WebSocket failed: {e}")

        # 4. Test Results API
        try:
            target = "scanme.nmap.org"
            async with session.get(f"{base_url}/api/targets/{target}/results") as resp:
                print(f"GET /api/targets/{target}/results status: {resp.status}")
                if resp.status == 200:
                    results = await resp.json()
                    print(f"📄 Results count: {len(results)}")
                    if len(results) > 0:
                        print(f"✅ Found {len(results)} result entries")
                        # Print first result type for debug
                        print(f"First result type: {results[0].get('type')}")
                    else:
                        print("❌ No results found in API response")
                else:
                    print("❌ Failed to fetch results")
        except Exception as e:
            print(f"❌ Results API failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_backend())
