#!/usr/bin/env python3
"""
Verification script for Mind Palace & Islands Plugin System REST APIs (urllib version).
"""
import sys
import os
import json
import logging
import urllib.request
import urllib.parse
import urllib.error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_mind_palace")

BASE_URL = "http://localhost:8000"

def api_request(path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    req_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            return response.status, json.loads(res_data) if res_data else {}
    except urllib.error.HTTPError as e:
        res_data = e.read().decode("utf-8")
        try:
            err_json = json.loads(res_data)
        except Exception:
            err_json = {"detail": res_data}
        return e.code, err_json
    except Exception as e:
        return 500, {"detail": str(e)}

def run_verification():
    logger.info("Starting Mind Palace & Islands Plugin System API verification...")
    logger.info("=" * 60)
    
    # 1. Create Mind Palace
    logger.info("1. Creating Mind Palace...")
    mp_payload = {
        "name": "test_palace_validation",
        "description": "Integration test mind palace for plugin verification."
    }
    status, mp_data = api_request("/api/mindpalace", "POST", mp_payload)
    if status != 200:
        logger.error(f"[FAIL] Create Mind Palace status: {status}, response: {mp_data}")
        return False
    mp_elem_id = mp_data["elem_id"]
    mp_uuid_id = mp_data["id"]
    logger.info(f"   [PASS] Mind Palace created successfully. Elem ID: {mp_elem_id}, UUID ID: {mp_uuid_id}")
    
    # 2. Create Page under Mind Palace
    logger.info("2. Creating Page under Mind Palace...")
    page_payload = {
        "title": "test_page_validation"
    }
    status, page_data = api_request(f"/api/mindpalace/{mp_elem_id}/page", "POST", page_payload)
    if status != 200:
        logger.error(f"[FAIL] Create Page status: {status}, response: {page_data}")
        return False
    page_elem_id = page_data["id"]
    page_uuid_id = page_data["page_id"]
    logger.info(f"   [PASS] Page created successfully. Elem ID: {page_elem_id}, UUID ID: {page_uuid_id}")
    
    # 3. Add Blocks to Page
    logger.info("3. Adding Blocks to Page...")
    blocks_payload = {
        "blocks": [
            {
                "type": "header",
                "content": "Transcendence Shamanism",
                "level": 2,
                "language": "text"
            },
            {
                "type": "text",
                "content": "The modular subgraphs represent islands of consciousness.",
                "level": 1,
                "language": "text"
            },
            {
                "type": "code",
                "content": "MATCH (mp:MindPalace) RETURN mp",
                "level": 1,
                "language": "cypher"
            }
        ]
    }
    status, save_data = api_request(f"/api/mindpalace/page/{page_elem_id}/blocks", "POST", blocks_payload)
    if status != 200:
        logger.error(f"[FAIL] Save Blocks status: {status}, response: {save_data}")
        return False
    logger.info("   [PASS] Blocks saved successfully.")
    
    # 4. Fetch Page and verify sorted blocks
    logger.info("4. Fetching Page and verifying blocks...")
    status, get_data = api_request(f"/api/mindpalace/page/{page_elem_id}")
    if status != 200:
        logger.error(f"[FAIL] Get Page status: {status}, response: {get_data}")
        return False
    if get_data["title"] != "test_page_validation":
        logger.error(f"[FAIL] Page title mismatch: {get_data['title']}")
        return False
        
    blocks = get_data["blocks"]
    if len(blocks) != 3:
        logger.error(f"[FAIL] Page block count mismatch: {len(blocks)}")
        return False
        
    if blocks[0]["type"] != "header" or blocks[0]["position"] != 0:
        logger.error(f"[FAIL] Block 0 mismatch: {blocks[0]}")
        return False
    if blocks[1]["type"] != "text" or blocks[1]["position"] != 1:
        logger.error(f"[FAIL] Block 1 mismatch: {blocks[1]}")
        return False
    if blocks[2]["type"] != "code" or blocks[2]["language"] != "cypher" or blocks[2]["position"] != 2:
        logger.error(f"[FAIL] Block 2 mismatch: {blocks[2]}")
        return False
        
    logger.info("   [PASS] Page title and block order verified.")
    
    # 5. Export Mind Palace Subgraph Plugin
    logger.info("5. Exporting Mind Palace Subgraph...")
    status, export_bundle = api_request(f"/api/mindpalace/{mp_elem_id}/export", "POST")
    if status != 200:
        logger.error(f"[FAIL] Export Palace status: {status}, response: {export_bundle}")
        return False
    nodes = export_bundle["export_data"]["nodes"]
    links = export_bundle["export_data"]["links"]
    logger.info(f"   Export bundle contains {len(nodes)} nodes and {len(links)} links.")
    
    # Verify presence of nodes
    node_labels = [n["label"] for n in nodes]
    if "MindPalace" not in node_labels or "Page" not in node_labels or "Block" not in node_labels:
        logger.error(f"[FAIL] Export bundle missing key labels: {node_labels}")
        return False
    logger.info("   [PASS] Export subgraph plugin structure verified.")
    
    # 6. Delete Page and verify cleanup
    logger.info("6. Deleting Page...")
    status, del_data = api_request(f"/api/mindpalace/page/{page_elem_id}", "DELETE")
    if status != 200:
        logger.error(f"[FAIL] Delete Page status: {status}, response: {del_data}")
        return False
        
    # Verify page is gone
    status, get_data = api_request(f"/api/mindpalace/page/{page_elem_id}")
    if status == 200:
        logger.error(f"[FAIL] Page still exists after deletion.")
        return False
    logger.info("   [PASS] Page deleted and cleaned from database.")
    
    # Delete Mind Palace node to check clean slate import
    logger.info("   Cleaning Mind Palace node for clean slate import test...")
    from db_logic import get_driver
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (mp:MindPalace {name: 'test_palace_validation'}) DETACH DELETE mp")
        
    # 7. Import Mind Palace Plugin JSON
    logger.info("7. Importing Mind Palace Plugin...")
    import_payload = {
        "export_data": export_bundle["export_data"]
    }
    status, import_data = api_request("/api/mindpalace/import", "POST", import_payload)
    if status != 200:
        logger.error(f"[FAIL] Import Palace status: {status}, response: {import_data}")
        return False
    logger.info("   [PASS] Import Palace execution returned success.")
    
    # 8. Verify DB node state after import
    logger.info("8. Verifying DB state after import...")
    with driver.session() as session:
        # Check MindPalace exists
        res = session.run("MATCH (mp:MindPalace {name: 'test_palace_validation'}) RETURN mp")
        if not res.single():
            logger.error("[FAIL] MindPalace node was not restored by import.")
            return False
            
        # Check Page and Blocks exist and are connected
        res = session.run(
            """
            MATCH (mp:MindPalace {name: 'test_palace_validation'})-[:HAS_PAGE]->(p:Page {title: 'test_page_validation'})
            MATCH (p)-[:HAS_BLOCK]->(b:Block)
            RETURN count(b) as block_count
            """
        )
        record = res.single()
        if not record or record["block_count"] != 3:
            logger.error(f"[FAIL] Page or Blocks relationship structure was not restored. Count: {record['block_count'] if record else 0}")
            return False
            
    logger.info("   [PASS] Subgraph nodes and relationships successfully re-established on import.")
    
    # 9. Clean up database
    logger.info("9. Cleaning up test nodes...")
    with driver.session() as session:
        session.run("MATCH (mp:MindPalace {name: 'test_palace_validation'})-[:HAS_PAGE]->(p:Page) MATCH (p)-[:HAS_BLOCK]->(b:Block) DETACH DELETE mp, p, b")
        session.run("MATCH (mp:MindPalace {name: 'test_palace_validation'}) DETACH DELETE mp")
    logger.info("   [PASS] Database cleaned.")
    
    logger.info("=" * 60)
    logger.info("All Mind Palace & Islands Plugin API tests passed successfully! 🎉")
    return True

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
