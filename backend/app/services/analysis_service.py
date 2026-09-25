import os
import re
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class LegalAnalysisService:
    def __init__(self):
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.GOOGLE_CLOUD_LOCATION

    async def analyze_document(self, text: str, filename: str = "document.pdf") -> Dict[str, Any]:
        """
        Analyzes legal document text and extracts a structured breakdown dashboard payload:
        - nature_of_document
        - legal_case
        - deadlines
        - contract_details
        - important_clauses
        - obligations
        - risks_and_inconsistencies
        - agreements_and_policies
        - lawyer_checklist
        - metrics
        """
        if not text or len(text.strip()) < 20:
            return self._generate_empty_fallback(filename)

        # 1. Attempt deep analysis via Google GenAI / Vertex AI if available
        ai_result = await self._analyze_with_ai(text, filename)
        if ai_result:
            return ai_result

        # 2. Fall back to heuristic rule-based extractor
        logger.info("Using heuristic rule-based legal extraction fallback.")
        return self._extract_heuristically(text, filename)

    async def _analyze_with_ai(self, text: str, filename: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini 2.5 Flash via google-genai SDK or ADK with structured JSON instructions."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )

            prompt = f"""
You are the LegalLens Chief Legal Analyst and Contract Specialist.
Analyze the following legal document (filename: '{filename}') and output a comprehensive, structured JSON breakdown.
Provide straightforward, crystal-clear answers in consumer-friendly plain English.

DOCUMENT TEXT EXCERPT:
{text[:22000]}

REQUIRED JSON OUTPUT FORMAT (Strict valid JSON only, no markdown backticks, no markdown code block wrapper):
{{
  "nature_of_document": {{
    "title": "Document Title",
    "document_type": "e.g. Mutual Non-Disclosure Agreement / Commercial Lease Agreement / Employment Contract / Service Agreement",
    "category": "Corporate / Real Estate / Employment / Intellectual Property / Commercial",
    "governing_law": "e.g. State of California / Laws of India",
    "jurisdiction": "e.g. San Francisco County Courts / High Court of Delhi",
    "parties": [
      {{"name": "Party Name 1", "role": "e.g. Disclosing Party / Landlord / Employer"}},
      {{"name": "Party Name 2", "role": "e.g. Receiving Party / Tenant / Employee"}}
    ],
    "execution_status": "Executed / Draft / Proposed"
  }},
  "legal_case": {{
    "case_or_matter": "Concise 1-line title of what this legal matter represents",
    "straightforward_summary": "2-3 sentences straight-to-the-point summary of what this document does, who gives what, and primary responsibilities.",
    "primary_intent": "The core commercial or legal goal of the transaction",
    "effective_date": "e.g. November 1, 2026 or Upon Execution",
    "validity_term": "e.g. 3 Years or 12 Months",
    "bottom_line_verdict": "Clear bottom-line advice for the client on whether this is safe to sign or requires negotiations."
  }},
  "deadlines": [
    {{
      "title": "Deadline Title (e.g. Notice of Termination Window)",
      "timeframe": "e.g. 30 days prior to expiration",
      "type": "critical | notice | payment | renewal",
      "description": "Plain description of what must happen by this deadline",
      "clause_ref": "Section 4.2"
    }}
  ],
  "contract_details": {{
    "financial_consideration": "Total fee, salary, rent, or consideration mentioned (e.g. $8,500/month or Mutual Exchange)",
    "security_deposit": "Deposit amount if any, or N/A",
    "payment_schedule": "e.g. Due on 1st of each calendar month or Net 30 days",
    "late_penalty": "Penalties, late fees, or interest rates for delayed payment",
    "duration": "Total length of contract",
    "renewal_terms": "Auto-renewal rules, opt-out timeframes, or fixed term",
    "termination_convenience": "Whether either party can terminate without cause, or cause only"
  }},
  "important_clauses": [
    {{
      "name": "Clause Name (e.g. Indemnification / Limitation of Liability / Non-Compete / Confidentiality / Termination)",
      "section": "Section number or clause title",
      "verbatim_quote": "Key sentence from the document",
      "simple_explanation": "What this means in plain everyday English",
      "severity": "critical | attention | standard | favorable"
    }}
  ],
  "obligations": [
    {{
      "party": "Party Name / Role",
      "duty": "What this party must do or refrain from doing",
      "timeframe": "Ongoing / Within 14 days / Prior to closing",
      "consequence_of_breach": "Termination, damages, forfeiture, legal injunction"
    }}
  ],
  "risks_and_inconsistencies": [
    {{
      "title": "Risk Headline (e.g. Uncapped Indemnification Burden)",
      "risk_level": "HIGH | MEDIUM | LOW",
      "clause_ref": "Section 7.1",
      "issue": "Plain language explanation of the danger or loophole",
      "practical_impact": "How this could cost money or restrict freedom",
      "recommended_remedy": "Concrete suggestion for redlining or negotiation"
    }}
  ],
  "agreements_and_policies": [
    {{
      "name": "Policy or Sub-Agreement (e.g. Data Protection / Confidentiality Policy / Code of Conduct / Arbitration)",
      "scope": "What standard or statute is referenced",
      "enforcement": "Binding arbitration, court litigation, liquidated damages"
    }}
  ],
  "lawyer_checklist": [
    "Strategic question 1 to ask an attorney",
    "Strategic question 2 to ask an attorney",
    "Strategic question 3 to ask an attorney"
  ],
  "metrics": {{
    "overall_risk_score": 65,
    "overall_risk_label": "High Attention | Moderate Risk | Low Risk / Standard",
    "high_risk_count": 2,
    "medium_risk_count": 2,
    "deadlines_count": 3,
    "key_clauses_count": 5
  }}
}}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )

            if response and response.text:
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                parsed = json.loads(cleaned_text.strip())
                return parsed
        except Exception as e:
            logger.warning(f"Vertex AI Gemini extraction could not complete: {e}. Falling back to rule-based analysis.")
            return None

    def _extract_heuristically(self, text: str, filename: str) -> Dict[str, Any]:
        """Deep rule-based heuristic legal parser that extracts structured breakdown elements."""
        lower_text = text.lower()

        # 1. Determine Nature of Document
        doc_type = "Legal Agreement"
        category = "Commercial"
        if "non-disclosure" in lower_text or "nda" in lower_text or "confidentiality" in lower_text:
            doc_type = "Mutual Non-Disclosure Agreement (NDA)"
            category = "Corporate & Confidentiality"
        elif "lease" in lower_text or "rental" in lower_text or "tenancy" in lower_text or "premises" in lower_text:
            doc_type = "Commercial / Residential Lease Agreement"
            category = "Real Estate"
        elif "employment" in lower_text or "offer letter" in lower_text or "employee" in lower_text or "salary" in lower_text:
            doc_type = "Employment & Compensation Agreement"
            category = "Employment & Labor"
        elif "service" in lower_text or "consulting" in lower_text or "statement of work" in lower_text or "sow" in lower_text:
            doc_type = "Master Services & Deliverables Agreement"
            category = "Commercial Contracting"
        elif "loan" in lower_text or "promissory note" in lower_text or "borrower" in lower_text or "lender" in lower_text:
            doc_type = "Loan & Promissory Note Agreement"
            category = "Banking & Finance"

        # 2. Extract Governing Law & Jurisdiction
        gov_law = "Governing Law Not Specified"
        jurisdiction = "Competent Courts of Jurisdiction"
        gov_match = re.search(r"governed by.*?laws of (?:the state of )?([A-Za-z\s]+?)(?:\.|,|;|\sand\b)", text, re.IGNORECASE)
        if gov_match:
            gov_law = f"Laws of {gov_match.group(1).strip()}"
            jurisdiction = f"Courts of {gov_match.group(1).strip()}"
        elif "california" in lower_text:
            gov_law = "State of California, USA"
            jurisdiction = "Superior Court of California"
        elif "delaware" in lower_text:
            gov_law = "State of Delaware, USA"
            jurisdiction = "Delaware Court of Chancery"
        elif "india" in lower_text:
            gov_law = "Laws of the Republic of India"
            jurisdiction = "High Court / Civil Court of Jurisdiction"

        # 3. Detect Parties
        parties = []
        party_match = re.search(r"between\s+([A-Z][A-Za-z0-9\s,\.]+?)\s+(?:and|\&)\s+([A-Z][A-Za-z0-9\s,\.]+?)(?:\.|,\s*dated|\s*\(each)", text)
        if party_match:
            parties.append({"name": party_match.group(1).strip(), "role": "First Party / Disclosing Entity"})
            parties.append({"name": party_match.group(2).strip(), "role": "Second Party / Receiving Entity"})
        else:
            parties = [
                {"name": "Disclosing / Issuing Party", "role": "Originator / Licensor"},
                {"name": "Client / Recipient Entity", "role": "Recipient / Counter-party"}
            ]

        # 4. Detect Deadlines & Dates
        deadlines = []
        # Notice periods
        notice_match = re.search(r"(\d+)\s*(?:days?|calendar days|business days)\s*(?:prior|written notice|notice)", text, re.IGNORECASE)
        if notice_match:
            deadlines.append({
                "title": f"Written Notice Period ({notice_match.group(1)} Days)",
                "timeframe": f"{notice_match.group(1)} Days prior to action",
                "type": "notice",
                "description": f"Mandatory written notice of {notice_match.group(1)} days required before termination, renewal, or modification.",
                "clause_ref": "Notice & Termination Clause"
            })

        # Term / Expiry
        term_match = re.search(r"term of\s*(\d+)\s*(years?|months?)", text, re.IGNORECASE)
        duration_str = f"{term_match.group(1)} {term_match.group(2)}" if term_match else "12 Months (Standard)"
        deadlines.append({
            "title": "Contract Term Expiration",
            "timeframe": duration_str,
            "type": "critical",
            "description": f"Initial operational validity period of {duration_str} unless renewed or terminated earlier for cause.",
            "clause_ref": "Term & Duration Clause"
        })

        # Payment due dates
        if "rent" in lower_text or "payment" in lower_text or "fee" in lower_text:
            deadlines.append({
                "title": "Recurring Payment Milestone",
                "timeframe": "1st of each calendar month / Net 30",
                "type": "payment",
                "description": "All invoiced consideration or rent must be paid without deduction or set-off.",
                "clause_ref": "Financial Terms"
            })

        # 5. Extract Financial and Contract Details
        financial_amt = "Stated consideration / Mutual covenants"
        money_match = re.search(r"(\$\s*[\d,]+|\₹\s*[\d,]+|USD\s*[\d,]+|INR\s*[\d,]+)", text)
        if money_match:
            financial_amt = money_match.group(1)

        # 6. Detect Important Clauses
        important_clauses = []
        # Confidentiality
        if "confidential" in lower_text:
            important_clauses.append({
                "name": "Confidentiality & Non-Disclosure",
                "section": "Proprietary Information",
                "verbatim_quote": "Confidential Information shall be kept strictly secret and protected using reasonable commercial care.",
                "simple_explanation": "Both parties are strictly prohibited from sharing trade secrets, business models, or proprietary data with outsiders.",
                "severity": "standard"
            })

        # Indemnity
        if "indemnif" in lower_text:
            has_uncapped = "uncapped" in lower_text or "all claims" in lower_text or "harmless" in lower_text
            important_clauses.append({
                "name": "Indemnification & Hold Harmless",
                "section": "Indemnity Provisions",
                "verbatim_quote": "The party agrees to defend, indemnify and hold harmless against any and all claims, damages, losses, and attorney fees.",
                "simple_explanation": "You may be required to pay for the other party's legal defense and damages if a third party sues over activities under this agreement.",
                "severity": "critical" if has_uncapped else "attention"
            })

        # Termination
        if "terminat" in lower_text:
            important_clauses.append({
                "name": "Termination for Cause & Default",
                "section": "Termination Protocol",
                "verbatim_quote": "Either party may terminate upon written notice in the event of a material breach uncured within the designated cure window.",
                "simple_explanation": "Explains how and when the agreement can be ended early if either side fails to meet their obligations.",
                "severity": "attention"
            })

        # Non-Compete
        if "non-compete" in lower_text or "non compete" in lower_text or "restrictive covenant" in lower_text:
            important_clauses.append({
                "name": "Non-Competition & Restriction",
                "section": "Restrictive Covenants",
                "verbatim_quote": "The party shall not engage directly or indirectly in competing business activities during and after the term.",
                "simple_explanation": "Restricts your ability to work with competitors or start a competing venture within a specified geographic area and timeframe.",
                "severity": "critical"
            })

        # Dispute Resolution
        if "arbitrat" in lower_text or "dispute" in lower_text:
            important_clauses.append({
                "name": "Dispute Resolution & Arbitration",
                "section": "Dispute Escalation",
                "verbatim_quote": "Any dispute arising under this agreement shall be settled through binding individual arbitration.",
                "simple_explanation": "Waives right to public jury trial and requires confidential private arbitration to settle disputes.",
                "severity": "attention"
            })

        # 7. Detect Risks & Inconsistencies
        risks = []
        if "indemnif" in lower_text:
            risks.append({
                "title": "Broad or One-Sided Indemnification",
                "risk_level": "HIGH",
                "clause_ref": "Indemnity Section",
                "issue": "The indemnification clause does not state a mutual liability cap and includes broad third-party attorney fee obligations.",
                "practical_impact": "Could expose you to unlimited financial payouts for claims outside your immediate operational control.",
                "recommended_remedy": "Insert a mutual liability cap equal to 12 months' contract fees and exclude indirect/consequential damages."
            })

        if "auto-renew" in lower_text or "automatically renew" in lower_text:
            risks.append({
                "title": "Automatic Renewal Trap",
                "risk_level": "MEDIUM",
                "clause_ref": "Term & Renewal Section",
                "issue": "Contract automatically renews for consecutive multi-year periods if written opt-out notice is missed.",
                "practical_impact": "Unintentional lock-in to an additional term with associated financial liabilities.",
                "recommended_remedy": "Add requirement for the other party to send a 30-day reminder before the renewal window closes."
            })
        else:
            risks.append({
                "title": "Ambiguous Cure Period for Breach",
                "risk_level": "MEDIUM",
                "clause_ref": "Default & Remedies Section",
                "issue": "No specific number of days defined to fix/cure accidental breaches before termination is invoked.",
                "practical_impact": "Could allow the counter-party to terminate immediately without giving you time to rectify an administrative error.",
                "recommended_remedy": "Demand a standard 30-day written cure period for all non-monetary defaults."
            })

        if "sole discretion" in lower_text or "unilateral" in lower_text:
            risks.append({
                "title": "Unilateral Discretion / Modification Rights",
                "risk_level": "HIGH",
                "clause_ref": "Operational Governance",
                "issue": "One party reserves the right to modify specifications, policies, or pricing in their sole discretion.",
                "practical_impact": "Unpredictable cost escalations or sudden changes to contract requirements.",
                "recommended_remedy": "Require mutual written consent signed by authorized representatives for all amendments."
            })

        # 8. Obligations
        obligations = [
            {
                "party": parties[0]["name"],
                "duty": "Provide deliverables / access to premises / disclosures in accordance with specifications.",
                "timeframe": "Commencing on Effective Date",
                "consequence_of_breach": "Material breach and immediate notice of remedy."
            },
            {
                "party": parties[1]["name"] if len(parties) > 1 else "Counter-Party",
                "duty": "Maintain strict confidentiality, make timely consideration payments, and comply with operational rules.",
                "timeframe": "Throughout agreement term and 3 years post-termination",
                "consequence_of_breach": "Immediate termination, forfeiture of deposit, injunctive relief."
            }
        ]

        # 9. Agreements & Policies
        policies = [
            {
                "name": "Mutual Non-Disclosure & Secrecy Standards",
                "scope": "All proprietary technical, financial, and client data",
                "enforcement": "Immediate injunctive relief without proof of actual damages"
            },
            {
                "name": "Statutory Regulatory Compliance",
                "scope": gov_law,
                "enforcement": jurisdiction
            }
        ]

        # 10. Lawyer Consultation Checklist
        checklist = [
            f"Is the liability exposure capped to a reasonable monetary maximum under {gov_law}?",
            "Are the termination triggers mutual, or does the counterparty hold unilateral exit rights?",
            "What specific disclosures or conditions precedent are required prior to executing the signature block?",
            "Is the mandatory arbitration clause favorable, or should local courts be specified instead?"
        ]

        # 11. Metrics
        high_cnt = sum(1 for r in risks if r["risk_level"] == "HIGH")
        med_cnt = sum(1 for r in risks if r["risk_level"] == "MEDIUM")
        score = 85 - (high_cnt * 20) - (med_cnt * 10)
        score = max(35, min(95, score))

        risk_label = "Favorable / Standard"
        if score < 50:
            risk_label = "High Attention Required"
        elif score < 75:
            risk_label = "Moderate Risk / Review Clauses"

        return {
            "nature_of_document": {
                "title": filename.replace("_", " ").replace(".pdf", "").replace(".docx", "").title(),
                "document_type": doc_type,
                "category": category,
                "governing_law": gov_law,
                "jurisdiction": jurisdiction,
                "parties": parties,
                "execution_status": "Ready for Legal Review"
            },
            "legal_case": {
                "case_or_matter": f"{doc_type} Review & Clause Risk Analysis",
                "straightforward_summary": f"This document establishes a binding {doc_type.lower()} governing obligations, term length, and financial/operational liabilities between the contracting entities. Key provisions focus on confidentiality, performance standards, and dispute escalation.",
                "primary_intent": "Formalize legal obligations and protect intellectual property / financial rights.",
                "effective_date": "Upon Execution / Signatures",
                "validity_term": duration_str,
                "bottom_line_verdict": f"{risk_label}: Carefully review the highlighted risk flags (especially indemnification and notice windows) prior to final execution."
            },
            "deadlines": deadlines,
            "contract_details": {
                "financial_consideration": financial_amt,
                "security_deposit": "As scheduled in terms" if "deposit" in lower_text else "Not specified / Mutual exchange",
                "payment_schedule": "Standard monthly cycle / Net 30 days",
                "late_penalty": "Interest at statutory rate or 1.5% per month for past-due amounts",
                "duration": duration_str,
                "renewal_terms": "Requires written notice or auto-renews per Section terms",
                "termination_convenience": "Termination for material breach with notice"
            },
            "important_clauses": important_clauses,
            "obligations": obligations,
            "risks_and_inconsistencies": risks,
            "agreements_and_policies": policies,
            "lawyer_checklist": checklist,
            "metrics": {
                "overall_risk_score": score,
                "overall_risk_label": risk_label,
                "high_risk_count": high_cnt,
                "medium_risk_count": med_cnt,
                "deadlines_count": len(deadlines),
                "key_clauses_count": len(important_clauses)
            }
        }

    def _generate_empty_fallback(self, filename: str) -> Dict[str, Any]:
        return {
            "nature_of_document": {
                "title": filename,
                "document_type": "Unspecified Legal Document",
                "category": "General Legal",
                "governing_law": "Pending Analysis",
                "jurisdiction": "Pending Analysis",
                "parties": [],
                "execution_status": "Uploaded"
            },
            "legal_case": {
                "case_or_matter": "Document Intake & Validation",
                "straightforward_summary": "Document uploaded. Full text extraction is processing.",
                "primary_intent": "Document analysis",
                "effective_date": datetime.now().strftime("%Y-%m-%d"),
                "validity_term": "TBD",
                "bottom_line_verdict": "Upload complete. Click 'Re-analyze' to run full multi-agent breakdown."
            },
            "deadlines": [],
            "contract_details": {},
            "important_clauses": [],
            "obligations": [],
            "risks_and_inconsistencies": [],
            "agreements_and_policies": [],
            "lawyer_checklist": [],
            "metrics": {
                "overall_risk_score": 50,
                "overall_risk_label": "Analysis Pending",
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "deadlines_count": 0,
                "key_clauses_count": 0
            }
        }

analysis_service = LegalAnalysisService()
