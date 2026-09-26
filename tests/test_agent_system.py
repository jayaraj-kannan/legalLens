import pytest
from legallens import prompts
from legallens import agent

def test_prompt_directives_and_safety_guardrails():
    # 1. Safety guardrails must be present in all sub-agent prompts
    assert "DO NOT provide definitive legal advice" in prompts.SAFETY_GUARDRAIL_INSTRUCTION
    assert "review findings with a certified legal professional" in prompts.SAFETY_GUARDRAIL_INSTRUCTION

    # 2. Check all specialized prompt constants
    all_prompts = [
        prompts.INTAKE_PARSER_INSTRUCTION,
        prompts.CLASSIFICATION_CLAUSE_INSTRUCTION,
        prompts.PLAIN_EXPLANATION_INSTRUCTION,
        prompts.DOCUMENT_QA_INSTRUCTION,
        prompts.CONTRACT_COMPARISON_INSTRUCTION,
        prompts.RISK_ATTENTION_INSTRUCTION,
        prompts.TIMELINE_OBLIGATION_INSTRUCTION,
        prompts.LAWYER_QUESTION_INSTRUCTION,
        prompts.MULTILINGUAL_INSTRUCTION,
        prompts.CITATION_EVIDENCE_INSTRUCTION,
        prompts.ORCHESTRATOR_INSTRUCTION,
    ]

    for p in all_prompts:
        assert isinstance(p, str)
        assert len(p.strip()) > 50
        assert "LegalLens" in p

def test_specialist_agents_configuration():
    specialists = [
        agent.intake_parser_agent,
        agent.classification_clause_agent,
        agent.plain_explanation_agent,
        agent.document_qa_agent,
        agent.contract_comparison_agent,
        agent.risk_attention_agent,
        agent.timeline_obligation_agent,
        agent.lawyer_question_agent,
        agent.multilingual_agent,
        agent.citation_evidence_agent,
    ]

    assert len(specialists) == 10

    for sa in specialists:
        assert sa.name is not None
        assert sa.description is not None
        assert len(sa.description) > 10
        assert sa.instruction is not None
        assert sa.model == agent.DEFAULT_MODEL

def test_orchestrator_root_agent():
    root = agent.root_agent
    assert root.name == "orchestrator_agent"
    assert root.model == "gemini-2.5-flash"
    assert len(root.sub_agents) == 10

    sub_agent_names = [sa.name for sa in root.sub_agents]
    expected_names = [
        "intake_parser_agent",
        "classification_clause_agent",
        "plain_explanation_agent",
        "document_qa_agent",
        "contract_comparison_agent",
        "risk_attention_agent",
        "timeline_obligation_agent",
        "lawyer_question_agent",
        "multilingual_agent",
        "citation_evidence_agent",
    ]
    for expected in expected_names:
        assert expected in sub_agent_names
