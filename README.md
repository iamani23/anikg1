# PM Knowledge Graph — Ask your project-management tools in plain English

An **RDF knowledge graph + ontology** for project-management tools (JIRA first,
others later), queried in natural language. You ask a question; **open-source
NLP + semantic parsing translates it into SPARQL** against a shared ontology;
the query runs over the graph and returns a grounded, verifiable answer.

> Status: **step 1, open-source NLP edition**. The ontology, the SPARQL layer,
> and the NL→SPARQL semantic parser (spaCy + rule-based) work today on bundled
> sample data. No LLM or API calls. The live JIRA connector is stubbed and
> clearly marked `TODO`.

---

## Why RDF + an ontology (instead of just SQL or raw API calls)?

- **A shared vocabulary.** JIRA, Asana, Linear and GitHub Issues all model the
  same ideas (project, issue, sprint, assignee, status) with different names.
  One ontology maps them all to the same concepts, so a single question works
  across tools.
- **Semantic parsing is deterministic.** The NL→SPARQL layer uses spaCy for
  entity recognition + rule-based pattern matching. No model hallucinations, no
  API costs, fully offline, and entirely auditable.
- **Answers are verifiable.** Every answer traces back to a SPARQL query you can
  read, re-run, and audit — not an opaque LLM guess.
- **Reasoning & links.** RDF lets you follow `blocks` / `isBlockedBy` /
  `epicLink` chains and, later, run OWL inference (e.g. "everything blocking a
  Done epic").

## How it works

```
                  ┌─────────────────────┐
  "Which bugs are │  NLP Semantic Parser │  ← entity recognition + rule patterns
   still open in  │  (spaCy + rules)    │
   the Payments   │  NL → SPARQL        │
   project?"      └──────────┬──────────┘
        ▲                    │  SPARQL
        │                    ▼
        │            ┌───────────────┐      ┌──────────────────────┐
   answer rows   ◄──│ Triplestore   │◄────│ JIRA / Asana / … ETL │
   + SPARQL query   │  (RDF KG)     │     │  maps records → RDF   │
                    └───────────────┘      └──────────────────────┘
```

1. **Ingest** — pull records from JIRA's REST API (step 2).
2. **Map** — convert each record to RDF triples using the [`pm:` ontology](ontology/pm.ttl).
3. **Store** — load triples into a triplestore (rdflib in-memory now; Fuseki/GraphDB later).
4. **Translate** — spaCy + rules turn the user's question into SPARQL (no LLM, no API calls).
5. **Execute & answer** — run the SPARQL and return result rows.

## Quick start (works on sample data, no JIRA or API keys needed)

```bash
pip install -e .
python -m spacy download en_core_web_sm  # one-time: download spaCy model

# Run a raw SPARQL query against the ontology + sample data
pm-kg query --sparql examples/queries.sparql --select 1

# Ask a natural-language question (fully offline, no API keys needed!)
pm-kg ask "Which open bugs in the Payments project are unassigned?"
```

`pm-kg ask` prints the generated SPARQL *and* the result rows, so you can see
exactly what the semantic parser extracted and how it queried the graph.

## Repository layout

```
ontology/            The pm: ontology (Turtle) + docs — the heart of the project
data/sample/         Small hand-written RDF dataset for demos & tests
src/pm_kg/
  config.py          Settings (JIRA creds, store path, data files)
  graph/store.py     Load ontology + data, run SPARQL (rdflib)
  ingestion/         JIRA client (stub) + JIRA-JSON → RDF mapper
  nl2sparql/
    semantic_parser.py Entity extraction + rule-based SPARQL generation
    prompt.py         Ontology schema summary (for future LLM bridge)
  pipeline.py        Ties ask → generate → execute → answer together
  cli.py             `pm-kg` command
examples/            Sample NL questions and expected SPARQL
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
