# The `pm:` ontology

`pm.ttl` is the semantic core of the project — a tool-agnostic vocabulary for
project-management data. Namespace: `https://w3id.org/pmkg/ontology#` (prefix
`pm:`).

## Design goals

1. **Tool-agnostic.** Model the shared concepts (Project, Issue, Sprint, Status,
   User) so JIRA, Asana, Linear and GitHub Issues can all map onto one graph.
2. **LLM-friendly.** Every class and property has an `rdfs:label` and
   `rdfs:comment`. Those comments are what the prompt builder feeds to the model,
   so writing good comments here directly improves query quality.
3. **Question-oriented.** Model the distinctions people actually ask about — e.g.
   `pm:StatusCategory` (To Do / In Progress / Done) so "open vs done" questions
   don't depend on brittle status-name string matching.

## Shape at a glance

- **Core:** `Project`, `Issue` (with subclasses `Epic`, `Story`, `Task`, `Bug`,
  `Subtask`), `Sprint`, `Board`, `Component`, `Version`.
- **Controlled values:** `IssueType`, `Status` + `StatusCategory`, `Priority`, `Label`.
- **People:** `User` (a `foaf:Agent`), plus `Comment` and `Worklog`.
- **Relationships:** `belongsToProject`, `hasStatus`, `assignee`, `reporter`,
  `inSprint`, `epicLink`, `parent`, `blocks`/`isBlockedBy`, `relatesTo`, …
- **Attributes:** `issueKey`, `summary`, `storyPoints`, `created`, `resolved`,
  `dueDate`, `sprintState`, `priorityRank`, …

## Extending it

- Add a new class/property with a clear `rdfs:label` + `rdfs:comment` — the
  prompt picks it up automatically (the schema summary is generated from this file).
- When mapping a new source tool, translate its fields to these terms in a mapper
  (see `src/pm_kg/ingestion/mapper.py`) rather than inventing new vocabulary.

## Validate

```bash
python -c "from rdflib import Graph; g=Graph().parse('ontology/pm.ttl'); print(len(g),'triples OK')"
```
