"""Store and load user-learned term mappings in the RDF graph.

When the parser is unsure about a term (e.g., "not assigned" → "unassigned"),
ask the user. If they confirm, store the mapping as an RDF triple so it's
remembered for future questions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from ..config import settings

# Namespace for user-learned mappings
EX = Namespace("https://w3id.org/pmkg/learned/")
PM = Namespace("https://w3id.org/pmkg/ontology#")

# Store user mappings in a separate file so they persist across runs
MAPPINGS_PATH = settings.ontology_path.parent / "user_learned_mappings.ttl"


def _load_mappings_graph() -> Graph:
    """Load user-learned mappings from disk, or create empty graph."""
    g = Graph()
    if MAPPINGS_PATH.exists():
        g.parse(MAPPINGS_PATH, format="turtle")
    return g


def ask_user_confirmation(question: str, suggested_interpretation: str) -> bool:
    """Ask the user for confirmation in an interactive prompt.

    Returns True if user says yes, False otherwise.
    """
    response = input(
        f"\n❓ Did you mean '{suggested_interpretation}' when you said '{question}'? "
        f"(yes/no): "
    ).strip().lower()
    return response in ("yes", "y")


def store_term_mapping(
    user_term: str, ontology_concept: str, graph: Graph | None = None
) -> None:
    """Store a user-provided term mapping as an RDF triple.

    Maps user_term to an ontology_concept. Example:
    - user_term: "not assigned"
    - ontology_concept: "unassigned"
    """
    if graph is None:
        graph = _load_mappings_graph()

    subj = EX[f"term_{user_term.lower().replace(' ', '_')}"]
    graph.add((subj, RDFS.label, Literal(user_term)))
    graph.add((subj, RDF.type, EX.UserLearnedTerm))
    graph.add((subj, EX.mapsTo, Literal(ontology_concept)))

    # Persist to disk
    graph.serialize(MAPPINGS_PATH, format="turtle")


def load_term_mappings() -> dict[str, str]:
    """Load all user-learned term mappings from the graph.

    Returns a dict: {user_term: ontology_concept}.
    """
    g = _load_mappings_graph()
    mappings: dict[str, str] = {}

    for subj in g.subjects(RDF.type, EX.UserLearnedTerm):
        label_obj = g.value(subj, RDFS.label)
        maps_to_obj = g.value(subj, EX.mapsTo)
        if label_obj and maps_to_obj:
            mappings[str(label_obj).lower()] = str(maps_to_obj)

    return mappings
