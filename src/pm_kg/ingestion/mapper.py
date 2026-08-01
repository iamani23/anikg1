"""Map raw JIRA issue JSON into RDF triples using the pm: ontology.

STEP 2 (partial). `map_issue` shows the intended field-to-property mapping for
the most important fields; extend it as you wire up the live client. The output
is an rdflib Graph you can serialize to Turtle or load straight into a store.
"""

from __future__ import annotations

from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

PM = Namespace("https://w3id.org/pmkg/ontology#")
DATA = Namespace("https://w3id.org/pmkg/data/")

# JIRA issue type name -> ontology class
_TYPE_TO_CLASS = {
    "Epic": PM.Epic,
    "Story": PM.Story,
    "Task": PM.Task,
    "Bug": PM.Bug,
    "Sub-task": PM.Subtask,
    "Subtask": PM.Subtask,
}


def _issue_uri(key: str) -> URIRef:
    return DATA[key]


def map_issue(issue: dict[str, Any], graph: Graph | None = None) -> Graph:
    """Add triples for a single JIRA issue JSON object to ``graph``."""
    g = graph if graph is not None else Graph()
    fields = issue.get("fields", {})
    key = issue.get("key")
    if not key:
        return g

    subj = _issue_uri(key)
    type_name = (fields.get("issuetype") or {}).get("name", "")
    g.add((subj, RDF.type, _TYPE_TO_CLASS.get(type_name, PM.Issue)))
    g.add((subj, PM.issueKey, Literal(key)))

    if fields.get("summary"):
        g.add((subj, PM.summary, Literal(fields["summary"])))
    if fields.get("created"):
        g.add((subj, PM.created, Literal(fields["created"], datatype=XSD.dateTime)))
    if fields.get("resolutiondate"):
        g.add((subj, PM.resolved, Literal(fields["resolutiondate"], datatype=XSD.dateTime)))

    project = fields.get("project") or {}
    if project.get("key"):
        proj_uri = DATA[f"project_{project['key']}"]
        g.add((subj, PM.belongsToProject, proj_uri))
        g.add((proj_uri, RDF.type, PM.Project))
        g.add((proj_uri, PM.projectKey, Literal(project["key"])))
        if project.get("name"):
            g.add((proj_uri, PM.name, Literal(project["name"])))

    assignee = fields.get("assignee")
    if assignee and assignee.get("accountId"):
        user_uri = DATA[f"user_{assignee['accountId']}"]
        g.add((subj, PM.assignee, user_uri))
        g.add((user_uri, RDF.type, PM.User))
        g.add((user_uri, PM.accountId, Literal(assignee["accountId"])))
        if assignee.get("displayName"):
            g.add((user_uri, PM.displayName, Literal(assignee["displayName"])))

    # TODO(step-2): status + status category, priority, sprint, epic link,
    # components, fix versions, story points, comments, worklogs, issue links.
    return g


def map_issues(issues: list[dict[str, Any]]) -> Graph:
    """Map a list of JIRA issues into one Graph."""
    g = Graph()
    for issue in issues:
        map_issue(issue, g)
    return g
