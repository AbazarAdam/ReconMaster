import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection and message reception"""
    
    # First, start a scan via API
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        print("🚀 Starting new scan...")
        async with session.post("http://127.0.0.1:8000/api/scans", json={"target": "wstest.com"}) as resp:
            if resp.status != 201:
                print(f"❌ Failed to start scan: {resp.status}")
                return
            data = await resp.json()
            scan_id = data["scan_id"]
            print(f"✅ Scan started: {scan_id}")
        
        # Now connect to WebSocket
        uri = f"ws://127.0.0.1:8000/ws/{scan_id}"
        print(f"\n🔌 Connecting to WebSocket: {uri}")
        
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ WebSocket connected!")
                
                # Listen for messages
                message_count = 0
                timeout_seconds = 15
                
                print(f"\n📡 Listening for messages (timeout: {timeout_seconds}s)...\n")
                
                try:
                    while True:
                        message = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
                        message_count += 1
                        data = json.loads(message)
                        
                        # Print message
                        msg_type = data.get('type', 'unknown')
                        if msg_type == 'log':
                            print(f"  📝 LOG: {data.get('message', '')}")
                        elif msg_type == 'status':
                            print(f"  🔄 STATUS: {data.get('status', '')}")
                        elif msg_type == 'phase':
                            print(f"  📊 PHASE: {data.get('phase', '')}")
                        elif msg_type == 'error':
                            print(f"  ❌ ERROR: {data.get('message', '')}")
                        else:
                            print(f"  ❓ {msg_type}: {data}")
                        
                except asyncio.TimeoutError:
                    print(f"\n⏱️ Timeout after {timeout_seconds}s")
                
                print(f"\n📊 Total messages received: {message_count}")
                
                if message_count == 0:
                    print("\n❌ NO MESSAGES RECEIVED!")
                    print("   This means the WebSocket connection works, but:")
                    print("   1. The engine is not calling progress_callback")
                    print("   2. OR the callback is failing silently")
                    print("   3. OR messages are being sent before we connect")
                else:
                    print(f"\n✅ WebSocket is working! Received {message_count} messages")
                
        except Exception as e:
            print(f"\n❌ WebSocket connection failed: {e}")
            print(f"   Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
