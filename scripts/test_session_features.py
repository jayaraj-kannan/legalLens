import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://localhost:8080/api/v1"

def request(method, path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, json.loads(content) if content else {"error": str(e)}

def main():
    print("=== Testing Consultation DB Persistence, Renaming & ADK Memory Mapping ===")
    
    # 1. Create a session
    status, res = request("POST", "/sessions", {"title": "Initial Consultation - MSA Review"})
    print(f"\n1. Create session -> status {status}: {res}")
    session_id = res.get("session_id") or res.get("id")
    assert status == 200, "Failed to create session"
    assert res["title"] == "Initial Consultation - MSA Review"
    
    # 2. Verify Session Details & ADK Session Initialization
    status, res = request("GET", f"/sessions/{session_id}")
    print(f"\n2. Fetch session details -> status {status}:")
    print(f"   ID: {res.get('id')}")
    print(f"   Title: {res.get('title')}")
    print(f"   State: {res.get('state')}")
    print(f"   ADK Synced: {res.get('adk_synced')}")
    assert status == 200, "Failed to get session"
    assert res.get("adk_synced") is True
    
    # 3. Rename consultation title
    new_title = "Acme Corp Master Services Agreement (MSA) - Final Review"
    status, res = request("PATCH", f"/sessions/{session_id}", {"title": new_title})
    print(f"\n3. Rename session -> status {status}: {res}")
    assert status == 200, "Failed to rename session"
    assert res["title"] == new_title
    
    # 4. Fetch list of sessions to verify DB persisted title in index
    status, res = request("GET", "/sessions")
    print(f"\n4. List sessions -> status {status}:")
    matching = [s for s in res if s.get("id") == session_id or s.get("session_id") == session_id]
    assert len(matching) > 0, "Session not found in list"
    print(f"   Found renamed session in DB: {matching[0]['title']}")
    assert matching[0]["title"] == new_title
    
    # 5. Save breakdown dashboard / details in DB
    mock_dashboard = {
        "nature_of_document": {
            "category": "Master Services Agreement",
            "jurisdiction": "State of New York, USA",
            "governing_law": "New York Commercial Law",
            "confidence": 0.95
        },
        "legal_case_summary": {
            "plain_verdict": "Enforceable commercial SaaS contract with mutual indemnities.",
            "overall_risk_score": 45,
            "overall_risk_level": "MODERATE"
        },
        "deadlines": [
            {
                "type": "Cure Period",
                "clause_ref": "Section 11.2",
                "timeframe": "30 days written notice",
                "urgency": "HIGH",
                "description": "Right to cure any material breach before termination."
            }
        ],
        "contract_details": {
            "parties": ["Acme Corp (Client)", "Global Tech Services LLC (Vendor)"],
            "effective_date": "2026-04-01",
            "total_value": "$150,000 ARR"
        },
        "key_clauses": [
            {
                "name": "Limitation of Liability",
                "severity": "HIGH",
                "verbatim_quote": "Liability capped at 12 months fees paid.",
                "analysis": "Standard commercial cap, acceptable risk."
            }
        ],
        "obligations": [
            {
                "party": "Client",
                "action": "Net 30 payment of invoice",
                "frequency": "Monthly",
                "clause": "Sec 4.1"
            }
        ],
        "risks_and_inconsistencies": [
            {
                "category": "Indemnity",
                "issue": "Uncapped IP indemnity obligation",
                "severity": "HIGH",
                "redline_recommendation": "Cap indemnity at 2x annual contract value."
            }
        ],
        "agreements_and_policies": [
            {
                "policy_name": "GDPR & SOC2 Compliance",
                "status": "COMPLIANT",
                "notes": "Data Processing Addendum attached"
            }
        ],
        "lawyer_checklist": [
            "Verify insurance coverage requirement in Sec 8",
            "Ensure dispute escalation specifies arbitration in NYC"
        ]
    }
    
    status, res = request("POST", f"/sessions/{session_id}/dashboard", mock_dashboard)
    print(f"\n5. Store breakdown dashboard details in DB -> status {status}: {res.get('message')}")
    assert status == 200, "Failed to store dashboard"
    
    # 6. Re-load consultation: fetch details and dashboard from DB
    status, loaded_dash = request("GET", f"/sessions/{session_id}/dashboard")
    analysis = loaded_dash.get("analysis") or loaded_dash
    print(f"\n6. Reload consultation dashboard from DB -> status {status}:")
    print(f"   Nature: {analysis.get('nature_of_document', {}).get('category')}")
    print(f"   Verdict: {analysis.get('legal_case_summary', {}).get('plain_verdict')}")
    print(f"   Risks count: {len(analysis.get('risks_and_inconsistencies', []))}")
    assert status == 200, "Failed to fetch dashboard"
    assert analysis["nature_of_document"]["category"] == "Master Services Agreement"
    
    # 7. Check session state mapping with ADK session memory
    status, res = request("GET", f"/sessions/{session_id}")
    print(f"\n7. Verify session details and ADK session synchronization:")
    print(f"   Session ID: {res.get('session_id')}")
    print(f"   Title: {res.get('title')}")
    print(f"   ADK Session ID: {res.get('adk_session_id')}")
    print(f"   State keys: {list(res.get('state', {}).keys())}")
    assert res["title"] == new_title
    assert "dashboard_breakdown" in res.get("state", {})
    
    print("\n✅ All consultation renaming, DB persistence, and ADK memory mapping tests PASSED!")

if __name__ == "__main__":
    main()
