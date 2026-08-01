# PM Knowledge Graph — Ask your project-management tools in plain English

An **RDF knowledge graph + ontology** for project-management tools (JIRA first,
others later), queried in natural language. You ask a question; an **LLM
translates it into SPARQL** against a shared ontology; the query runs over the
graph and returns a grounded, verifiable answer.

> Status: **early scaffold / step 1**. The ontology, the SPARQL layer, and the
> NL→SPARQL prompt pipeline work today on the bundled sample data. The live
> JIRA connector is stubbed and clearly marked `TODO`.

---

## Why RDF + an ontology (instead of just SQL or raw API calls)?

- **A shared vocabulary.** JIRA, Asana, Linear and GitHub Issues all model the
  same ideas (project, issue, sprint, assignee, status) with different names.
  One ontology maps them all to the same concepts, so a single question works
  across tools.
- **LLMs generate better SPARQL when handed a schema.** The ontology *is* the
  schema. We feed its classes, properties, and comments into the prompt, which
  dramatically reduces hallucinated queries versus free-form SQL over an unknown
  table layout.
- **Answers are verifiable.** Every answer traces back to a SPARQL query you can
  read, re-run, and audit — not an opaque model guess.
- **Reasoning & links.** RDF lets you follow `blocks` / `isBlockedBy` /
  `epicLink` chains and, later, run OWL inference (e.g. "everything blocking a
  Done epic").

## How it works

```
                    ┌──────────────┐
  "Which bugs are   │   LLM (Claude)│  ← ontology schema is injected here
   still open in    │  NL → SPARQL  │
   the Payments     └──────┬───────┘
   epic?"                  │  SPARQL
        ▲                  ▼
        │            ┌───────────┐      ┌──────────────────────┐
   answer in         │ Triplestore│◄────│ JIRA / Asana / … ETL │
   plain English  ◄──│  (RDF KG)  │     │  maps records → RDF   │
                     └───────────┘      └──────────────────────┘
```

1. **Ingest** — pull records from JIRA's REST API.
2. **Map** — convert each record to RDF triples using the [`pm:` ontology](ontology/pm.ttl).
3. **Store** — load triples into a triplestore (rdflib file store now; Fuseki/GraphDB later).
4. **Translate** — an LLM turns the user's question into SPARQL, prompted with the ontology.
5. **Execute & answer** — run the SPARQL, then (optionally) verbalize the result set.

## Quick start (works on sample data, no JIRA needed)

```bash
pip install -e .

# Run a raw SPARQL query against the ontology + sample data
pm-kg query --sparql examples/queries.sparql --select 1

# Ask a natural-language question (needs ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-...
pm-kg ask "Which open bugs in the Payments project are unassigned?"
```

`pm-kg ask` prints the generated SPARQL *and* the result, so you can see exactly
what the model asked the graph.

## Repository layout

```
ontology/            The pm: ontology (Turtle) + docs — the heart of the project
data/sample/         Small hand-written RDF dataset for demos & tests
src/pm_kg/
  config.py          Settings (model, JIRA creds, store path)
  graph/store.py     Load ontology + data, run SPARQL (rdflib)
  ingestion/         JIRA client (stub) + JIRA-JSON → RDF mapper
  nl2sparql/         Prompt builder (injects ontology) + LLM generator
  pipeline.py        Ties ask → generate → execute → answer together
  cli.py             `pm-kg` command
examples/            Sample NL questions and their SPARQL
docs/architecture.md Deeper design notes and roadmap
```

## Roadmap

- [x] **Step 1 — Foundation:** ontology, SPARQL layer, NL→SPARQL prompt, sample data, CLI.
- [ ] **Step 2 — Live JIRA:** implement the REST client + incremental sync into the store.
- [ ] **Step 3 — Production store:** run against Apache Jena Fuseki / GraphDB.
- [ ] **Step 4 — Guardrails:** SPARQL validation, query repair loop, read-only enforcement.
- [ ] **Step 5 — More sources:** Asana, Linear, GitHub Issues mapped to the same ontology.
- [ ] **Step 6 — API + UI:** FastAPI endpoint and a lightweight chat front end.

## License

MIT — see [LICENSE](LICENSE).
