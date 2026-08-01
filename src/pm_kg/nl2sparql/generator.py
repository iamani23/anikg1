"""Generate SPARQL from natural language using open-source NLP (spaCy + rules).

No LLM or API calls required — fully offline semantic parsing.
"""

from .semantic_parser import generate_sparql

__all__ = ["generate_sparql"]
