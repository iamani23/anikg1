"""Interactive query learning: ask user to confirm interpretation and learn from feedback.

Two-way learning:
1. Positive: "Yes, that's what I meant" → store the pattern
2. Negative: "No to all" → use NLP to infer actual intent and store it
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import spacy
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from ..config import settings

EX = Namespace("https://w3id.org/pmkg/learned/")
PM = Namespace("https://w3id.org/pmkg/ontology#")

LEARNED_QUERIES_PATH = settings.ontology_path.parent / "learned_query_patterns.ttl"


def _load_learned_queries() -> Graph:
    """Load previously learned query patterns."""
    g = Graph()
    if LEARNED_QUERIES_PATH.exists():
        g.parse(LEARNED_QUERIES_PATH, format="turtle")
    return g


def ask_confirm_interpretation(question: str, generated_sparql: str) -> bool:
    """Ask user if the generated SPARQL matches their intent.

    Shows the SPARQL so user understands what was generated.
    """
    print("\n" + "=" * 70)
    print("Generated SPARQL:")
    print("=" * 70)
    print(generated_sparql)
    print("=" * 70)
    response = input(
        "\n✓ Does this match what you meant? (yes/no/explain): "
    ).strip().lower()
    return response in ("yes", "y")


def get_user_explanation() -> str:
    """When user says 'no' or 'explain', ask what they actually meant."""
    print("\n❌ Let me understand better...")
    explanation = input(
        "What did you actually want to find? (be specific): "
    ).strip()
    return explanation


def store_learned_query(
    question: str, interpretation: str, sparql: str, graph: Graph | None = None
) -> None:
    """Store a confirmed query pattern as RDF.

    Creates a triple linking the question to its correct interpretation.
    """
    if graph is None:
        graph = _load_learned_queries()

    subj = EX[f"query_{hash(question.lower()) % (10 ** 8)}"]
    graph.add((subj, RDF.type, EX.LearnedQueryPattern))
    graph.add((subj, RDFS.label, Literal(question)))
    graph.add((subj, EX.userInterpretation, Literal(interpretation)))
    graph.add((subj, EX.generatedSPARQL, Literal(sparql)))

    graph.serialize(LEARNED_QUERIES_PATH, format="turtle")


def parse_user_intent(question: str, user_explanation: str) -> dict[str, Any]:
    """Use NLP to parse what the user actually meant.

    Returns a dict with extracted entities/concepts from the explanation.
    """
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        return {"raw_text": user_explanation, "confidence": 0.0}

    doc = nlp(user_explanation)

    intent = {
        "raw_text": user_explanation,
        "entities": {},
        "verbs": [],
        "confidence": 0.8,
    }

    # Extract named entities
    for ent in doc.ents:
        if ent.label_ not in intent["entities"]:
            intent["entities"][ent.label_] = []
        intent["entities"][ent.label_].append(ent.text)

    # Extract action verbs
    for token in doc:
        if token.pos_ == "VERB" and not token.is_stop:
            intent["verbs"].append(token.text)

    # Look for specific keywords
    keywords = {
        "open": any(w in user_explanation.lower() for w in ["open", "not done"]),
        "done": "done" in user_explanation.lower(),
        "unassigned": any(w in user_explanation.lower() for w in ["unassigned", "not assigned"]),
        "assigned": any(w in user_explanation.lower() for w in ["assigned to", "assignee"]),
        "priority": any(w in user_explanation.lower() for w in ["high", "low", "priority"]),
        "sprint": "sprint" in user_explanation.lower(),
    }
    intent["keywords"] = {k: v for k, v in keywords.items() if v}

    return intent


def learn_from_no(
    original_question: str, user_explanation: str
) -> tuple[dict[str, Any], str]:
    """When user rejects all interpretations, learn from their explanation.

    Returns the parsed intent and a summary for confirmation.
    """
    intent = parse_user_intent(original_question, user_explanation)

    # Build a human-readable summary
    summary_parts = []
    if intent["keywords"]:
        summary_parts.append(f"Looking for: {', '.join(intent['keywords'].keys())}")
    if intent["verbs"]:
        summary_parts.append(f"Action: {', '.join(intent['verbs'])}")
    if intent["entities"].get("PERSON"):
        summary_parts.append(f"People: {', '.join(intent['entities']['PERSON'])}")

    summary = " | ".join(summary_parts) if summary_parts else intent["raw_text"]

    return intent, summary


def confirm_learned_intent(summary: str) -> bool:
    """Ask user to confirm our understanding of their intent."""
    response = input(
        f"\nSo you're looking for: {summary}\n\nCorrect? (yes/no): "
    ).strip().lower()
    return response in ("yes", "y")


def store_learned_intent(
    question: str, intent: dict[str, Any], graph: Graph | None = None
) -> None:
    """Store the learned intent (when user says no, then yes to clarification)."""
    if graph is None:
        graph = _load_learned_queries()

    subj = EX[f"intent_{hash(question.lower()) % (10 ** 8)}"]
    graph.add((subj, RDF.type, EX.LearnedUserIntent))
    graph.add((subj, RDFS.label, Literal(question)))
    graph.add((subj, EX.parsedIntent, Literal(str(intent))))

    for keyword in intent.get("keywords", {}):
        graph.add((subj, EX.hasKeyword, Literal(keyword)))

    graph.serialize(LEARNED_QUERIES_PATH, format="turtle")
