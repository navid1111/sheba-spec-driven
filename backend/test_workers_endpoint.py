"""Test admin workers endpoint."""
import httpx
import json

try:
    r = httpx.get('http://localhost:8000/admin/workers?page=1&page_size=5', timeout=10)
    print(f'Status: {r.status_code}')
    
    if r.status_code == 200:
        data = r.json()
        print(f'Total workers: {data.get("total")}')
        print(f'Workers returned: {len(data.get("workers", []))}')
        print(f'Has next page: {data.get("has_next")}')
        print(f'\nFirst worker (if any):')
        if data.get("workers"):
            worker = data["workers"][0]
            print(f'  ID: {worker["id"]}')
            print(f'  Name: {worker["name"]}')
            print(f'  Performance: {worker["performance"]}')
            print(f'  Flags: {worker["flags"]}')
        
        print(f'\nFull response:')
        print(json.dumps(data, indent=2))
    else:
        print(f'Error: {r.json()}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
