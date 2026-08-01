"""End-to-end: natural-language question -> SPARQL -> results -> answer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .graph.store import GraphStore, default_store
from .nl2sparql.generator import generate_sparql


@dataclass
class AskResult:
    question: str
    sparql: str
    rows: list[dict[str, Any]]


def ask(question: str, store: GraphStore | None = None) -> AskResult:
    """Answer a natural-language question against the knowledge graph.

    1. Generate SPARQL from the question (semantic parser, no LLM).
    2. Execute it against the store.
    """
    store = store or default_store()
    sparql = generate_sparql(question)
    rows = store.query(sparql)
    return AskResult(question=question, sparql=sparql, rows=rows)
