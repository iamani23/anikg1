"""Tests for the ontology-aware prompt builder (no network / LLM needed)."""

from pm_kg.nl2sparql.prompt import build_prompt, summarize_ontology


def test_summary_includes_key_terms():
    summary = summarize_ontology()
    for term in ["pm:Issue", "pm:hasStatus", "pm:assignee", "pm:issueKey"]:
        assert term in summary


def test_prompt_contains_question_and_schema():
    prompt = build_prompt("Which bugs are open?")
    assert "Which bugs are open?" in prompt
    assert "pm:Bug" in prompt
    assert "PREFIX pm:" in prompt
