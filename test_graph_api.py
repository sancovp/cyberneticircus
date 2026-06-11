import urllib.request
import json
import sys

print("Diagnosing /api/graph endpoint...")
try:
    with urllib.request.urlopen("http://localhost:8000/api/graph?name=JesterCoreOne", timeout=5.0) as res:
        data = json.loads(res.read().decode('utf-8'))
        print(f"Success! Retrieved {len(data.get('nodes', []))} nodes and {len(data.get('links', []))} links.")
        for node in data.get('nodes', [])[:5]:
            print(f"  - Node: id={node.get('id')}, name={node.get('name')}, active={node.get('active_tag')}, highlighted={node.get('highlighted')}")
except Exception as e:
    print(f"Error calling /api/graph: {e}")
    import traceback
    traceback.print_exc()
