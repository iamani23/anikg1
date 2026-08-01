"""Semantic parser: convert natural-language questions to SPARQL using spaCy + rules.

No LLM or API calls. Instead: entity recognition (issue keys, user names, statuses)
+ pattern matching against known question types, with fallback SPARQL templates.

Learns from user feedback: when unsure about a term, asks the user and stores
the mapping in the RDF graph for future use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import spacy

from .user_mappings import ask_user_confirmation, load_term_mappings, store_term_mapping

# Load spaCy's pretrained English model (small version, ~40 MB).
# On first import, if not installed, download with: python -m spacy download en_core_web_sm
NLP = None
try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    pass  # Lazy load on first use with a clear error message


def _ensure_model_loaded() -> None:
    """Ensure spaCy model is loaded; raise clear error if not."""
    global NLP
    if NLP is not None:
        return
    raise RuntimeError(
        "spaCy model 'en_core_web_sm' not found. Download it with:\n"
        "  python -m spacy download en_core_web_sm\n"
        "If spacy is not installed, run: pip install -e ."
    )

PREFIXES = """PREFIX pm:   <https://w3id.org/pmkg/ontology#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>"""


@dataclass
class ExtractedEntities:
    """Entities recognized in the question."""

    issue_type: str | None = None  # "bug", "story", "task", "epic"
    issue_key: str | None = None  # "PAY-123"
    status_category: str | None = None  # "open", "done", "in progress"
    user_name: str | None = None  # User display name or mention
    sprint: str | None = None  # "active", "closed", or sprint name
    project_key: str | None = None  # "PAY", "ENG", etc.
    assignment: str | None = None  # "assigned", "unassigned"
    priority: str | None = None  # "high", "highest", "low"
    verb: str | None = None  # "show", "list", "find", "which"
    raw_question: str = ""


def _extract_entities(question: str) -> ExtractedEntities:
    """Use regex + spaCy to recognize PM-specific entities.

    Learns from user feedback: if unsure about a term, asks the user and
    stores the mapping for future queries.
    """
    _ensure_model_loaded()

    q_lower = question.lower()
    ents = ExtractedEntities(raw_question=question)
    user_mappings = load_term_mappings()

    # Issue type
    for typ in ["bug", "story", "task", "epic", "subtask"]:
        if typ in q_lower:
            ents.issue_type = typ
            break

    # Issue key (e.g. PAY-123)
    match = re.search(r"\b([A-Z]+)-(\d+)\b", question)
    if match:
        ents.issue_key = match.group(0)
        ents.project_key = match.group(1)

    # Status / status category
    if any(w in q_lower for w in ["open", "unresolved", "not done", "incomplete"]):
        ents.status_category = "open"
    elif any(w in q_lower for w in ["done", "closed", "resolved", "complete"]):
        ents.status_category = "done"
    elif any(w in q_lower for w in ["in progress", "in-progress", "active", "wip"]):
        ents.status_category = "in progress"

    # Assignment: detect negations first ("not a single", "none of", etc.)
    negation_patterns = [
        "not a single", "not any", "not one", "none of", "no members",
        "no one", "nobody", "not assigned", "unassigned"
    ]
    for pattern in negation_patterns:
        if pattern in q_lower:
            mapped_value = user_mappings.get(pattern)
            if mapped_value == "unassigned":
                ents.assignment = "unassigned"
                break
            elif pattern not in ["unassigned"]:
                # Ambiguous term: ask user for confirmation
                if ask_user_confirmation(pattern, "unassigned"):
                    ents.assignment = "unassigned"
                    store_term_mapping(pattern, "unassigned")
                break
            else:
                ents.assignment = "unassigned"
                break

    # If no negation found but "assigned" appears, ask for clarification
    if not ents.assignment and ("assigned" in q_lower or "assignee" in q_lower):
        if "not" in q_lower or "no" in q_lower or "none" in q_lower:
            # Likely asking for unassigned but in a complex way
            if ask_user_confirmation("assigned (with negation)", "unassigned"):
                ents.assignment = "unassigned"
                store_term_mapping("assigned with negation", "unassigned")
        else:
            ents.assignment = "assigned"

    # Priority
    for prio in ["highest", "high", "medium", "low", "lowest"]:
        if prio in q_lower:
            ents.priority = prio
            break

    # Sprint
    if "active" in q_lower and "sprint" in q_lower:
        ents.sprint = "active"
    elif "sprint" in q_lower:
        if "closed" in q_lower:
            ents.sprint = "closed"

    # Action verb
    doc = NLP(question)
    for token in doc:
        if token.pos_ == "VERB":
            if token.text.lower() in ["show", "list", "find", "get", "which", "what"]:
                ents.verb = token.text.lower()
                break

    # User name (spaCy NER for PERSON)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            ents.user_name = ent.text
            break

    return ents


def _build_open_issues_query(ents: ExtractedEntities) -> str:
    """Build a SPARQL query for 'which/show [type] issues are open' patterns."""
    type_clause = ""
    if ents.issue_type:
        type_name = ents.issue_type.capitalize()
        if ents.issue_type == "subtask":
            type_name = "Subtask"
        type_clause = f"; a pm:{type_name}"

    project_clause = ""
    if ents.project_key:
        project_clause = (
            f"""; pm:belongsToProject ?proj .
  ?proj pm:projectKey "{ents.project_key}" """
        )

    return f"""{PREFIXES}

SELECT ?key ?summary ?status WHERE {{
  ?issue{type_clause} ;
         pm:issueKey ?key ;
         pm:summary ?summary ;
         pm:hasStatus ?s{project_clause} .
  ?s pm:name ?status ;
     pm:inStatusCategory ?cat .
  ?cat pm:name ?catName .
  FILTER (?catName != "Done")
}}
ORDER BY ?key"""


def _build_unassigned_query(ents: ExtractedEntities) -> str:
    """Build a query for unassigned issues."""
    type_clause = ""
    if ents.issue_type:
        type_name = ents.issue_type.capitalize()
        if ents.issue_type == "subtask":
            type_name = "Subtask"
        type_clause = f"a pm:{type_name} ;\n         "

    status_lines = ""
    if ents.status_category == "open":
        status_lines = """;
         pm:hasStatus ?s .
  ?s pm:inStatusCategory ?cat ;
     pm:name ?catName .
  FILTER (?catName != "Done")"""

    return f"""{PREFIXES}

SELECT ?key ?summary WHERE {{
  ?issue {type_clause}pm:issueKey ?key ;
         pm:summary ?summary{status_lines} .
  FILTER NOT EXISTS {{ ?issue pm:assignee ?u }}
}}"""


def _build_by_assignee_query(ents: ExtractedEntities) -> str:
    """Build a query for issues by assignee."""
    if not ents.user_name:
        return _build_open_issues_query(ents)

    return f"""{PREFIXES}

SELECT ?key ?summary ?statusName WHERE {{
  ?user pm:displayName "{ents.user_name}" .
  ?issue pm:assignee ?user ;
         pm:issueKey ?key ;
         pm:summary ?summary ;
         pm:hasStatus ?s .
  ?s pm:name ?statusName .
}}
ORDER BY ?key"""


def _build_sprint_query(ents: ExtractedEntities) -> str:
    """Build a query for issues in a sprint."""
    state = ents.sprint or "active"

    return f"""{PREFIXES}

SELECT ?key ?summary ?status ?assignee WHERE {{
  ?sprint pm:sprintState "{state}" .
  ?issue pm:inSprint ?sprint ;
         pm:issueKey ?key ;
         pm:summary ?summary ;
         pm:hasStatus ?s .
  ?s pm:name ?status .
  OPTIONAL {{ ?issue pm:assignee ?user . ?user pm:displayName ?assignee }}
}}
ORDER BY ?key"""


def generate_sparql(question: str) -> str:
    """Parse a natural-language question and return SPARQL.

    Uses entity extraction + rule-based pattern matching. No API calls.
    """
    ents = _extract_entities(question)
    q_lower = question.lower()

    # Route to the appropriate query builder based on patterns
    if ents.assignment == "unassigned":
        return _build_unassigned_query(ents)
    elif "sprint" in q_lower:
        return _build_sprint_query(ents)
    elif ents.user_name:
        return _build_by_assignee_query(ents)
    elif any(w in q_lower for w in ["open", "unresolved", "not done", "in progress"]):
        return _build_open_issues_query(ents)
    elif any(w in q_lower for w in ["done", "closed", "resolved", "complete"]):
        status_clause = "Done"
        type_clause = ""
        if ents.issue_type:
            type_name = ents.issue_type.capitalize()
            if ents.issue_type == "subtask":
                type_name = "Subtask"
            type_clause = f"; a pm:{type_name}"

        return f"""{PREFIXES}

SELECT ?key ?summary WHERE {{
  ?issue{type_clause} ;
         pm:issueKey ?key ;
         pm:summary ?summary ;
         pm:hasStatus ?s .
  ?s pm:name ?status ;
     pm:inStatusCategory ?cat .
  ?cat pm:name "{status_clause}" .
}}
ORDER BY ?key"""

    # Default: list all issues of a given type
    if ents.issue_type:
        type_name = ents.issue_type.capitalize()
        if ents.issue_type == "subtask":
            type_name = "Subtask"
        return f"""{PREFIXES}

SELECT ?key ?summary ?status WHERE {{
  ?issue a pm:{type_name} ;
         pm:issueKey ?key ;
         pm:summary ?summary ;
         pm:hasStatus ?s .
  ?s pm:name ?status .
}}
ORDER BY ?key"""

    # Fallback: all issues
    return f"""{PREFIXES}

SELECT ?key ?summary ?status WHERE {{
  ?issue pm:issueKey ?key ;
         pm:summary ?summary ;
         pm:hasStatus ?s .
  ?s pm:name ?status .
}}
LIMIT 20"""
