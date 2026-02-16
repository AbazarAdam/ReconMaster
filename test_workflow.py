import asyncio
import aiohttp
import json

async def test_complete_workflow():
    """Test the complete scan workflow"""
    base_url = "http://127.0.0.1:8000"
    
    print("=" * 60)
    print("RECONMASTER DASHBOARD TEST")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. Start a new scan
        print("\n[1] Starting new scan for 'testdomain.com'...")
        async with session.post(f"{base_url}/api/scans", json={"target": "testdomain.com"}) as resp:
            if resp.status != 201:
                print(f"❌ Failed to start scan: {resp.status}")
                return
            scan_data = await resp.json()
            scan_id = scan_data["scan_id"]
            print(f"✅ Scan started: {scan_id}")
        
        # 2. Wait a bit for scan to progress
        print("\n[2] Waiting 5 seconds for scan to progress...")
        await asyncio.sleep(5)
        
        # 3. Check scan status
        print("\n[3] Checking scan status...")
        async with session.get(f"{base_url}/api/scans/{scan_id}") as resp:
            if resp.status != 200:
                print(f"❌ Failed to get scan: {resp.status}")
                return
            scan_info = await resp.json()
            print(f"✅ Scan status: {scan_info['status']}")
            print(f"   Target: {scan_info['target']}")
        
        # 4. Check if results exist
        print("\n[4] Checking scan results...")
        async with session.get(f"{base_url}/api/scans/{scan_id}/results") as resp:
            if resp.status != 200:
                print(f"❌ Failed to get results: {resp.status}")
                return
            results = await resp.json()
            print(f"✅ Found {len(results)} result entries")
            
            # Count by type
            types = {}
            for r in results:
                t = r.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
            
            if types:
                print("   Result types:")
                for t, count in types.items():
                    print(f"     - {t}: {count}")
            else:
                print("   ⚠️ No results yet (scan may still be running)")
        
        # 5. Test target-based results (for existing scans)
        print("\n[5] Testing target-based results for 'example.com'...")
        async with session.get(f"{base_url}/api/targets/example.com/results") as resp:
            if resp.status != 200:
                print(f"❌ Failed: {resp.status}")
            else:
                results = await resp.json()
                print(f"✅ Found {len(results)} results for example.com")
                
                # Sample one result
                if results:
                    sample = results[0]
                    print(f"   Sample result:")
                    print(f"     - Type: {sample['type']}")
                    print(f"     - Module: {sample['module']}")
                    data = sample['data']
                    if isinstance(data, list) and len(data) > 0:
                        print(f"     - Data (first item): {list(data[0].keys())}")
                    elif isinstance(data, dict):
                        print(f"     - Data fields: {list(data.keys())}")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        print(f"\nTo view the scan progress page, visit:")
        print(f"  http://127.0.0.1:8000/scan/{scan_id}")
        print(f"\nTo view results (after scan completes), visit:")
        print(f"  http://127.0.0.1:8000/results/testdomain.com")

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
