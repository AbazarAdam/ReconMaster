import asyncio
import aiohttp
import json

async def run_diagnostic():
    base_url = "http://localhost:8000"
    target = "example.com" # Using the target from the successful scan
    
    print(f"🔍 Running diagnostic for target: {target}")
    
    async with aiohttp.ClientSession() as session:
        # 1. Check Scans
        print("\n[1] Checking Scans API...")
        async with session.get(f"{base_url}/api/scans") as resp:
            if resp.status != 200:
                print(f"❌ Failed to list scans: {resp.status}")
                return
            scans = await resp.json()
            print(f"✅ Found {len(scans)} scans.")
            for s in scans:
                print(f"   - {s['id']} | {s['target']} | {s['status']}")

        # 2. Fetch Results
        print(f"\n[2] Fetching Results for {target}...")
        async with session.get(f"{base_url}/api/targets/{target}/results") as resp:
            if resp.status != 200:
                print(f"❌ Failed to get results: {resp.status}")
                return
            results = await resp.json()
            print(f"✅ API returned {len(results)} raw result entries.")
            
            # 3. Simulate Frontend Parsing
            print("\n[3] Simulating Frontend Parsing (results.js logic)...")
            data = {
                "subdomains": [],
                "ports": [],
                "http": [],
                "screenshots": [],
                "vulns": []
            }
            
            for res in results:
                type_ = res.get("type")
                item = res.get("data")
                module = res.get("module")
                
                # print(f"   DEBUG: Processing type='{type_}' from module='{module}'")
                
                items = item if isinstance(item, list) else [item]
                
                for entry in items:
                    if type_ == 'subdomain':
                        data["subdomains"].append(entry)
                    elif type_ == 'portscan' or type_ == 'port': # Simulating fix
                        data["ports"].append(entry)
                    elif type_ == 'http':
                        data["http"].append(entry)
                    elif type_ == 'screenshot':
                        data["screenshots"].append(entry)
                    elif type_ == 'shodan' or type_ == 'github' or type_ == 'cloud_buckets' or type_ == 'cloud_bucket': # Simulating fix
                        data["vulns"].append(entry)
                    else:
                        print(f"   ⚠️ Unhandled type: {type_}")

            print("\n[4] Parsed Data Counts:")
            print(f"   - Subdomains: {len(data['subdomains'])}")
            print(f"   - Ports: {len(data['ports'])}")
            print(f"   - HTTP: {len(data['http'])}")
            print(f"   - Screenshots: {len(data['screenshots'])}")
            print(f"   - Vulns: {len(data['vulns'])}")
            
            if len(data['ports']) > 0 and len(data['ports']) < 5:
                print(f"   - Sample Port: {data['ports'][0]}")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
