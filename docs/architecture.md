# Architecture & design notes

## The pipeline

```
question ──▶ prompt builder ──▶ LLM ──▶ SPARQL ──▶ triplestore ──▶ rows ──▶ answer
              (injects              (Claude)          (rdflib /
               ontology schema)                        Fuseki)
```

Each stage is a small, independently testable module:

| Stage | Module | Status |
|-------|--------|--------|
| Ontology (schema) | `ontology/pm.ttl` | ✅ done |
| Schema → prompt | `pm_kg.nl2sparql.prompt` | ✅ done |
| NL → SPARQL | `pm_kg.nl2sparql.generator` | ✅ done (needs API key) |
| Store + SPARQL exec | `pm_kg.graph.store` | ✅ done (rdflib) |
| JIRA fetch | `pm_kg.ingestion.jira_client` | 🚧 stub |
| JIRA → RDF | `pm_kg.ingestion.mapper` | 🚧 partial |
| Orchestration | `pm_kg.pipeline` | ✅ done |
| CLI | `pm_kg.cli` | ✅ done |

## Why the ontology goes into the prompt

Text-to-query models fail mostly by referencing fields that don't exist. By
serializing the ontology's classes, properties, and comments into the prompt
(`summarize_ontology`), the model is grounded in the real schema. Because the
summary is generated from `pm.ttl` at runtime, the prompt never drifts from the
actual vocabulary.

## Choosing a triplestore (step 3)

The local rdflib store is perfect for development and tests. For real data,
swap in a SPARQL endpoint via `PMKG_SPARQL_ENDPOINT`:

- **Apache Jena Fuseki** — lightweight, easy to self-host, great for getting started.
- **GraphDB** — richer OWL reasoning and tooling.
- **Blazegraph / Amazon Neptune** — for larger, managed deployments.

The `GraphStore` interface is deliberately thin so a `RemoteStore` backed by
`SPARQLWrapper` can be dropped in without touching the pipeline.

## Guardrails to add (step 4)

- **Read-only enforcement:** reject anything that isn't SELECT/ASK/CONSTRUCT
  (no INSERT/DELETE/DROP) before executing generated SPARQL.
- **Validation + repair loop:** if a query errors or returns nothing, feed the
  error back to the LLM once to self-correct.
- **LIMIT injection:** cap result sizes to keep responses bounded.
- **Provenance:** always surface the generated SPARQL (the CLI already does this)
  so answers are auditable.

## Multi-source (step 5)

Each source tool gets its own client + mapper that targets the *same* `pm:`
vocabulary. Named graphs (one per source) let you keep provenance while querying
across all of them at once.
