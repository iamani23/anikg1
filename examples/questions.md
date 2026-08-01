# Example natural-language questions

These are the kinds of questions the LLM should be able to answer by generating
SPARQL against the `pm:` ontology. Run them with:

```bash
pm-kg ask "your question here"
```

| # | Natural-language question | What it exercises |
|---|---------------------------|-------------------|
| 1 | Which issues in the Payments project are still open? | status category, project filter |
| 2 | List the open bugs that nobody is assigned to. | class filter + unassigned (NOT EXISTS) |
| 3 | How many story points does each person have in the active sprint? | aggregation, sprint state |
| 4 | What is blocking PAY-20? | issue-link traversal |
| 5 | Show every issue under the "Card payments checkout" epic and its status. | epic link |
| 6 | Which highest-priority issues are not done yet? | priority + status category |
| 7 | Who reported the most bugs? | grouping by reporter |
| 8 | What did Alice Chen resolve in Sprint 23? | user + sprint + resolved date |

The bundled `data/sample/sample_data.ttl` contains enough data to answer all of
these. As you connect live JIRA (step 2), the same questions keep working — only
the data behind the graph changes.
