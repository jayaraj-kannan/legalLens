import os
from dotenv import load_dotenv

# Ensure enterprise / Vertex AI configuration is loaded from .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from google.adk.agents.llm_agent import Agent
from legallens import prompts

DEFAULT_MODEL = 'gemini-2.5-flash'

# 1. Document Intake, Parser & Structure Specialist
intake_parser_agent = Agent(
    model=DEFAULT_MODEL,
    name='intake_parser_agent',
    description='Specialist for parsing document structure, metadata, OCR text, headings, tables, signatures, and document quality.',
    instruction=prompts.INTAKE_PARSER_INSTRUCTION,
)

# 2. Classification & Clause Extraction Specialist
classification_clause_agent = Agent(
    model=DEFAULT_MODEL,
    name='classification_clause_agent',
    description='Specialist for classifying document type and identifying key clauses (payment, termination, liability, confidentiality, jurisdiction, etc.).',
    instruction=prompts.CLASSIFICATION_CLAUSE_INSTRUCTION,
)

# 3. Plain-Language Explanation Specialist
plain_explanation_agent = Agent(
    model=DEFAULT_MODEL,
    name='plain_explanation_agent',
    description='Specialist for converting dense legal jargon into plain, easy-to-understand explanations and practical summaries.',
    instruction=prompts.PLAIN_EXPLANATION_INSTRUCTION,
)

# 4. Grounded Document Q&A Specialist
document_qa_agent = Agent(
    model=DEFAULT_MODEL,
    name='document_qa_agent',
    description='Specialist for answering questions strictly grounded in the document text without speculation.',
    instruction=prompts.DOCUMENT_QA_INSTRUCTION,
)

# 5. Contract Comparison Specialist
contract_comparison_agent = Agent(
    model=DEFAULT_MODEL,
    name='contract_comparison_agent',
    description='Specialist for comparing multiple documents/contracts and highlighting additions, deletions, and risk-shifting modifications.',
    instruction=prompts.CONTRACT_COMPARISON_INSTRUCTION,
)

# 6. Risk, Important Clause & Attention Specialist
risk_attention_agent = Agent(
    model=DEFAULT_MODEL,
    name='risk_attention_agent',
    description='Specialist for detecting high-risk, unbalanced, or hidden provisions, and explaining why they require careful review.',
    instruction=prompts.RISK_ATTENTION_INSTRUCTION,
)

# 7. Timeline, Obligations & Action Checklist Specialist
timeline_obligation_agent = Agent(
    model=DEFAULT_MODEL,
    name='timeline_obligation_agent',
    description='Specialist for chronological date timelines, party-by-party obligations, deadlines, and actionable pre/post-signing checklists.',
    instruction=prompts.TIMELINE_OBLIGATION_INSTRUCTION,
)

# 8. Lawyer Question Generator & Consultation Prep Specialist
lawyer_question_agent = Agent(
    model=DEFAULT_MODEL,
    name='lawyer_question_agent',
    description='Specialist for generating strategic, high-value questions for consultation with a qualified legal professional.',
    instruction=prompts.LAWYER_QUESTION_INSTRUCTION,
)

# 9. Multilingual Translation & Explanation Specialist
multilingual_agent = Agent(
    model=DEFAULT_MODEL,
    name='multilingual_agent',
    description='Specialist for translating and explaining legal findings in Indian regional languages (Tamil, Hindi, Telugu, etc.).',
    instruction=prompts.MULTILINGUAL_INSTRUCTION,
)

# 10. Citation & Evidence Verification Specialist
citation_evidence_agent = Agent(
    model=DEFAULT_MODEL,
    name='citation_evidence_agent',
    description='Specialist for verifying answers and anchoring claims to exact clause numbers, page numbers, and verbatim quotes.',
    instruction=prompts.CITATION_EVIDENCE_INSTRUCTION,
)

# Central Response Orchestrator Agent
root_agent = Agent(
    model=DEFAULT_MODEL,
    name='orchestrator_agent',
    description='Lead LegalLens Response Orchestrator that determines user intent and coordinates specialist legal sub-agents.',
    instruction=prompts.ORCHESTRATOR_INSTRUCTION,
    sub_agents=[
        intake_parser_agent,
        classification_clause_agent,
        plain_explanation_agent,
        document_qa_agent,
        contract_comparison_agent,
        risk_attention_agent,
        timeline_obligation_agent,
        lawyer_question_agent,
        multilingual_agent,
        citation_evidence_agent,
    ],
)
