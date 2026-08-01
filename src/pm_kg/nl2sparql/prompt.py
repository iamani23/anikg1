"""Build the LLM prompt that turns a natural-language question into SPARQL.

The key idea: we describe the ontology (classes, properties, comments) directly
in the prompt so the model generates queries grounded in the real schema instead
of guessing. The schema summary is derived from the ontology file itself, so it
stays in sync automatically.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, RDFS
from rdflib.namespace import OWL, RDF

from ..config import settings

PREFIXES = """PREFIX pm:   <https://w3id.org/pmkg/ontology#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>"""


def summarize_ontology(ontology_path: Path | None = None) -> str:
    """Produce a compact, human-readable schema description from the ontology."""
    g = Graph()
    g.parse(ontology_path or settings.ontology_path, format="turtle")

    def described(subjects) -> list[str]:
        lines = []
        for s in sorted(subjects, key=str):
            label = g.value(s, RDFS.label)
            comment = g.value(s, RDFS.comment)
            qname = s.n3(g.namespace_manager)
            desc = f"- {qname}"
            if label:
                desc += f" ({label})"
            if comment:
                desc += f": {comment}"
            lines.append(desc)
        return lines

    classes = set(g.subjects(RDF.type, OWL.Class))
    obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    data_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))

    parts = [
        "CLASSES:",
        *described(classes),
        "",
        "RELATIONSHIPS (object properties):",
        *described(obj_props),
        "",
        "ATTRIBUTES (datatype properties):",
        *described(data_props),
    ]
    return "\n".join(parts)


SYSTEM_INSTRUCTIONS = """You translate questions about project-management data \
into SPARQL 1.1 queries over an RDF knowledge graph.

Rules:
- Use ONLY the classes and properties from the schema provided. Do not invent terms.
- Always include the prefix declarations shown.
- Prefer matching statuses via pm:hasStatus/pm:inStatusCategory for "open" (To Do
  or In Progress) vs "done" questions, rather than string-matching status names.
- "Unassigned" means no pm:assignee triple exists (use FILTER NOT EXISTS or OPTIONAL + !BOUND).
- Return a SELECT query unless the question is strictly yes/no (then ASK).
- Select human-readable fields (issue keys, summaries, names), not opaque URIs, when possible.
- Output ONLY the SPARQL query inside a single ```sparql code block. No commentary."""


def build_prompt(question: str, ontology_path: Path | None = None) -> str:
    """Assemble the full user-message prompt for a given question."""
    schema = summarize_ontology(ontology_path)
    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"# Ontology schema\n{schema}\n\n"
        f"# Required prefixes\n{PREFIXES}\n\n"
        f"# Question\n{question}\n\n"
        f"Write the SPARQL query."
    )
