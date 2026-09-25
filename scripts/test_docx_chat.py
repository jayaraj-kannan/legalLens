import urllib.request
import urllib.parse
import json
import zipfile
import io
import xml.etree.ElementTree as ET

BASE_URL = "http://localhost:8080/api/v1"

def create_sample_docx_bytes():
    """Generates a valid PK-compressed Microsoft Word (.docx) binary file."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        # Standard Word OpenXML document.xml
        xml_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>SOFTWARE DEVELOPMENT AND CONSULTING AGREEMENT</w:t></w:r></w:p>
    <w:p><w:r><w:t>This Agreement is dated November 15, 2026, by and between Horizon AI Labs Ltd ("Developer") and Apex Financial Holdings ("Client").</w:t></w:r></w:p>
    <w:p><w:r><w:t>Section 1. Scope of Work. Developer shall deliver custom algorithmic risk models within 90 days.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Section 2. Compensation. Total project fee is $250,000 USD payable in three milestones with Net 15 days payment terms.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Section 3. Limitation of Liability. Under no circumstances shall Developer's aggregate liability exceed the total fees paid under this Agreement. Neither party shall be liable for indirect or consequential damages.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Section 4. Termination. Either party may terminate with 30 days written notice for any reason.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Section 5. Governing Law and Arbitration. This contract is governed by New York Law with binding AAA arbitration in Manhattan.</w:t></w:r></w:p>
  </w:body>
</w:document>"""
        z.writestr("word/document.xml", xml_content)
        # Required [Content_Types].xml
        types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
        z.writestr("[Content_Types].xml", types_xml)
    return bio.getvalue()

def upload_multipart(filename, content_bytes, user_id, session_id):
    boundary = "----WebKitFormBoundaryLegalLensDocx7MA4"
    body_parts = []
    body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"user_id\"\r\n\r\n{user_id}\r\n".encode("utf-8"))
    body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"session_id\"\r\n\r\n{session_id}\r\n".encode("utf-8"))
    header = f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n"
    body_parts.append(header.encode("utf-8") + content_bytes + b"\r\n")
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    
    full_body = b"".join(body_parts)
    req = urllib.request.Request(
        f"{BASE_URL}/documents/upload",
        data=full_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def request_json(method, path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        content = resp.read().decode("utf-8")
        return resp.status, json.loads(content) if content else {}

def main():
    print("=== Testing DOCX PK-Compressed Binary Parsing & Multi-Agent Chat ===")
    
    # 1. Create session
    status, sess = request_json("POST", "/sessions", {
        "title": "DOCX Consulting Agreement Review",
        "user_id": "docx_tester"
    })
    session_id = sess.get("session_id") or sess.get("id")
    print(f"\n1. Created consultation: {session_id}")
    
    # 2. Upload actual PK-compressed .docx file
    docx_bytes = create_sample_docx_bytes()
    print(f"\n2. Generated PK file: {len(docx_bytes)} bytes (starts with: {docx_bytes[:4]})")
    status, upload_res = upload_multipart("Horizon_Apex_Agreement.docx", docx_bytes, "docx_tester", session_id)
    assert status == 200, "DOCX upload failed"
    doc_id = upload_res["document"]["id"]
    snippet = upload_res["document"]["extracted_text_snippet"]
    print(f"   Uploaded doc ID: {doc_id}")
    print(f"   Extracted Text Snippet:\n   '{snippet[:120]}...'")
    assert not snippet.startswith("PK"), "Snippet contains raw PK compression!"
    assert "SOFTWARE DEVELOPMENT" in snippet, "Snippet did not extract OpenXML text!"
    
    # 3. Query agent about the DOCX agreement
    print("\n3. Querying multi-agent assistant about the agreement terms...")
    status, agent_res = request_json("POST", "/agent/query", {
        "session_id": session_id,
        "user_id": "docx_tester",
        "prompt": "What is the liability cap and what are the payment terms?",
        "document_ids": [doc_id]
    })
    print(f"   Agent Status: {status}")
    print(f"   Responding Agent: {agent_res.get('agent_name')}")
    print(f"   Response Text:\n   {agent_res.get('response_text')}\n")
    
    assert "PK-compressed" not in agent_res.get("response_text"), "Agent still complained about PK compression!"
    print("✅ SUCCESS: DOCX PK-compressed file was parsed and processed cleanly by the AI Agent!")

if __name__ == "__main__":
    main()
