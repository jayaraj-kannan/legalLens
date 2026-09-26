import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.analysis_service import LegalAnalysisService

@pytest.mark.asyncio
async def test_analyze_document_empty_and_fallback():
    service = LegalAnalysisService()
    
    # 1. Empty string
    empty_res = await service.analyze_document("", "test.pdf")
    assert empty_res["nature_of_document"]["title"] == "test.pdf"
    assert empty_res["nature_of_document"]["document_type"] == "Unspecified Legal Document"
    assert empty_res["metrics"]["overall_risk_score"] == 50

    # 2. Too short text (< 20 chars)
    short_res = await service.analyze_document("Short note", "contract.docx")
    assert short_res["nature_of_document"]["document_type"] == "Unspecified Legal Document"

@pytest.mark.asyncio
async def test_analyze_with_ai_success_and_exception():
    service = LegalAnalysisService()
    sample_text = "This is a mutual non-disclosure agreement between Acme Corp and Beta LLC governed by laws of California."

    # 1. AI success with markdown code block
    mock_response = MagicMock()
    mock_response.text = '```json\n{"nature_of_document": {"title": "NDA", "document_type": "NDA"}}\n```'
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_mod = MagicMock(Client=MagicMock(return_value=mock_client))
    mock_google = MagicMock(genai=mock_genai_mod)

    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai_mod}):
        res = await service._analyze_with_ai(sample_text, "nda.pdf")
        assert res is not None
        assert res["nature_of_document"]["document_type"] == "NDA"

    # 2. AI success with plain JSON
    mock_response.text = '{"nature_of_document": {"title": "Plain NDA"}}'
    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai_mod}):
        res_plain = await service._analyze_with_ai(sample_text, "nda.pdf")
        assert res_plain["nature_of_document"]["title"] == "Plain NDA"

    # 3. AI exception -> returns None
    mock_client.models.generate_content.side_effect = Exception("Vertex AI quota exceeded")
    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai_mod}):
        res_err = await service._analyze_with_ai(sample_text, "nda.pdf")
        assert res_err is None

@pytest.mark.asyncio
async def test_extract_heuristically_nda_category():
    service = LegalAnalysisService()
    text = """
    MUTUAL NON-DISCLOSURE AGREEMENT
    This Agreement is entered into between Acme Corporation and Beta Industries LLC.
    This agreement shall be governed by the laws of the State of California.
    Any disputes shall be submitted to the exclusive jurisdiction of the Courts of San Francisco.
    Term: This agreement shall remain in effect for a period of 2 years.
    Deposit: No security deposit required. Total consideration is $10,000 for evaluation services.
    Section 1. Confidential Information: Each party shall maintain in strict confidence.
    Section 2. Indemnification: Each party agrees to indemnify and hold harmless the other party.
    Section 3. Termination: Either party may terminate with 30 days prior written notice.
    Section 4. Automatic renewal: This agreement shall auto-renew annually unless notice is given.
    Section 5. Limitation of liability: In no event shall liability exceed total fees paid.
    Section 6. Non-compete: Receiving party agrees not to compete for 12 months.
    Section 7. Arbitration: All claims shall be settled by binding arbitration.
    """
    res = service._extract_heuristically(text, "acme_beta_nda.pdf")

    assert res["nature_of_document"]["document_type"] == "Mutual Non-Disclosure Agreement (NDA)"
    assert res["nature_of_document"]["category"] == "Corporate & Confidentiality"
    assert "California" in res["nature_of_document"]["governing_law"]
    assert len(res["nature_of_document"]["parties"]) >= 1
    assert len(res["important_clauses"]) >= 1
    assert len(res["risks_and_inconsistencies"]) >= 1
    assert res["metrics"]["overall_risk_score"] > 0
    assert "acme beta nda" in res["nature_of_document"]["title"].lower()

@pytest.mark.asyncio
async def test_extract_heuristically_lease_category():
    service = LegalAnalysisService()
    text = """
    COMMERCIAL LEASE AGREEMENT
    Landlord leases to Tenant the commercial premises located at 100 Main St.
    Monthly rent consideration is $5,500. Security deposit of $11,000 is due at execution.
    Term of 3 years beginning on the commencement date.
    Tenant obligation: Tenant shall maintain insurance and pay utilities within 10 days.
    Default cure period: Landlord may terminate upon 5 days notice of default.
    Governing law: This lease is governed by laws of New York.
    """
    res = service._extract_heuristically(text, "commercial_lease.docx")
    assert res["nature_of_document"]["document_type"] == "Commercial / Residential Lease Agreement"
    assert res["nature_of_document"]["category"] == "Real Estate"
    assert res["contract_details"]["security_deposit"] == "As scheduled in terms"

@pytest.mark.asyncio
async def test_extract_heuristically_employment_and_services_and_loan():
    service = LegalAnalysisService()

    # Employment
    emp_text = "EMPLOYMENT CONTRACT: Company offers employee a salary of $120,000 per year with operational duties."
    res_emp = service._extract_heuristically(emp_text, "offer_letter.pdf")
    assert res_emp["nature_of_document"]["category"] == "Employment & Labor"

    # Services / SOW
    sow_text = "MASTER SERVICES AGREEMENT and Statement of Work for consulting deliverables and software engineering."
    res_sow = service._extract_heuristically(sow_text, "sow.pdf")
    assert res_sow["nature_of_document"]["category"] == "Commercial Contracting"

    # Loan / Promissory
    loan_text = "PROMISSORY NOTE: Borrower promises to pay to the order of Lender the principal sum."
    res_loan = service._extract_heuristically(loan_text, "loan_note.pdf")
    assert res_loan["nature_of_document"]["category"] == "Banking & Finance"

    # Fallback generic
    generic_text = "General formal memorandum of understanding between alpha and beta regarding mutual intentions."
    res_gen = service._extract_heuristically(generic_text, "memo.pdf")
    assert res_gen["nature_of_document"]["document_type"] == "Legal Agreement"
    assert res_gen["nature_of_document"]["category"] == "Commercial"

@pytest.mark.asyncio
async def test_risk_score_threshold_labels():
    service = LegalAnalysisService()
    
    # Text with heavy risks (uncapped indemnification, automatic renewal, binding arbitration, non-compete, sole discretion)
    high_risk_text = """
    AGREEMENT with uncapped indemnification and hold harmless.
    One party in its sole discretion may alter all terms without limitation.
    Automatic renewal annually.
    Binding arbitration with waiver of court rights.
    Non-compete obligation.
    Vague cure period without remedy days.
    """
    res = service._extract_heuristically(high_risk_text, "high_risk.pdf")
    assert res["metrics"]["overall_risk_score"] < 50
    assert res["metrics"]["overall_risk_label"] == "High Attention Required"

@pytest.mark.asyncio
async def test_analyze_document_ai_early_return():
    service = LegalAnalysisService()
    ai_dict = {"nature_of_document": {"title": "AI Early Return"}}
    with patch.object(service, "_analyze_with_ai", new_callable=AsyncMock, return_value=ai_dict):
        res = await service.analyze_document("Valid length legal agreement text for testing.", "contract.pdf")
        assert res == ai_dict

@pytest.mark.asyncio
async def test_analyze_with_ai_code_fence_no_json_tag():
    service = LegalAnalysisService()
    mock_response = MagicMock()
    mock_response.text = '```\n{"nature_of_document": {"title": "No Tag JSON"}}\n```'
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_mod = MagicMock(Client=MagicMock(return_value=mock_client))
    mock_google = MagicMock(genai=mock_genai_mod)

    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai_mod}):
        res = await service._analyze_with_ai("Sample document text exceeding minimum length.", "doc.pdf")
        assert res["nature_of_document"]["title"] == "No Tag JSON"

def test_extract_heuristically_jurisdictions():
    service = LegalAnalysisService()
    # California fallback
    res_cal = service._extract_heuristically("Agreement involving california operations.", "doc.pdf")
    assert "California" in res_cal["nature_of_document"]["governing_law"]

    # Delaware fallback
    res_del = service._extract_heuristically("Agreement involving delaware corporation.", "doc.pdf")
    assert "Delaware" in res_del["nature_of_document"]["governing_law"]

    # India fallback
    res_ind = service._extract_heuristically("Agreement involving india business operations.", "doc.pdf")
    assert "India" in res_ind["nature_of_document"]["governing_law"]

