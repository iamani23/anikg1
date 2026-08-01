"""Command-line interface: `pm-kg`.

Examples:
    pm-kg query --sparql examples/queries.sparql --select 1
    pm-kg query --text 'SELECT ?k WHERE { ?i pm:issueKey ?k } LIMIT 5'
    pm-kg ask "Which open bugs in Payments are unassigned?"
    pm-kg schema        # print the ontology summary sent to the LLM
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .graph.store import default_store
from .nl2sparql.prompt import summarize_ontology


def _print_rows(rows: list[dict]) -> None:
    if not rows:
        print("(no results)")
        return
    print(json.dumps(rows, indent=2, ensure_ascii=False))


def _split_sparql_file(text: str) -> list[str]:
    """Split a .sparql file into individual queries on lines that are just '---'."""
    blocks, current = [], []
    for line in text.splitlines():
        if line.strip() == "---":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current and "".join(current).strip():
        blocks.append("\n".join(current))
    return blocks


def cmd_query(args: argparse.Namespace) -> int:
    store = default_store()
    if args.text:
        _print_rows(store.query(args.text))
        return 0
    if args.sparql:
        queries = _split_sparql_file(Path(args.sparql).read_text())
        indices = [args.select - 1] if args.select else range(len(queries))
        for i in indices:
            print(f"\n--- query {i + 1} ---")
            print(queries[i].strip())
            print("--- result ---")
            _print_rows(store.query(queries[i]))
        return 0
    print("Provide --text '<sparql>' or --sparql <file>", file=sys.stderr)
    return 2


def cmd_ask(args: argparse.Namespace) -> int:
    from .graph.store import default_store
    from .nl2sparql.generator import generate_sparql
    from .nl2sparql.query_learner import (
        ask_confirm_interpretation,
        confirm_learned_intent,
        get_user_explanation,
        learn_from_no,
        store_learned_intent,
        store_learned_query,
    )

    question = args.question
    store = default_store()

    # Step 1: Generate SPARQL
    sparql = generate_sparql(question)

    # Step 2: Ask for confirmation with SPARQL shown
    if ask_confirm_interpretation(question, sparql):
        # User confirmed: store the pattern and run the query
        store_learned_query(question, "confirmed by user", sparql)
        print("\n✓ Learned this pattern!\n")
        rows = store.query(sparql)
        print("Result:\n")
        _print_rows(rows)
        return 0

    # Step 3: User said no – ask for their actual intent
    user_explanation = get_user_explanation()

    # Step 4: Parse user's intent using NLP
    intent, summary = learn_from_no(question, user_explanation)

    # Step 5: Confirm our understanding
    if confirm_learned_intent(summary):
        store_learned_intent(question, intent)
        print("✓ Learned your intent! I'll remember this pattern.\n")
        # Regenerate SPARQL based on learned intent
        sparql = generate_sparql(question)
        rows = store.query(sparql)
        print("Result:\n")
        _print_rows(rows)
        return 0
    else:
        print("\n❌ Sorry, I'm still not understanding correctly.")
        print("Could you rephrase your question more simply?")
        return 1


def cmd_schema(_: argparse.Namespace) -> int:
    print(summarize_ontology())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pm-kg", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("query", help="Run raw SPARQL against the graph")
    q.add_argument("--text", help="Inline SPARQL query")
    q.add_argument("--sparql", help="Path to a .sparql file (queries separated by '---')")
    q.add_argument("--select", type=int, help="Run only the Nth query from the file")
    q.set_defaults(func=cmd_query)

    a = sub.add_parser("ask", help="Ask a natural-language question (needs ANTHROPIC_API_KEY)")
    a.add_argument("question", help="The question, in quotes")
    a.set_defaults(func=cmd_ask)

    s = sub.add_parser("schema", help="Print the ontology summary sent to the LLM")
    s.set_defaults(func=cmd_schema)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
