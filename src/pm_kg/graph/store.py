"""The RDF store: load the ontology + data and run SPARQL over it.

Uses a local, in-memory rdflib graph by default so everything runs with no
external services. Point ``PMKG_SPARQL_ENDPOINT`` at a triplestore (e.g. Apache
Jena Fuseki or GraphDB) to run the same queries against a production store.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from rdflib import Graph

from ..config import settings


class GraphStore:
    """Wraps an rdflib Graph loaded with the ontology and data files."""

    def __init__(
        self,
        ontology_path: Path | None = None,
        data_paths: Iterable[Path] | None = None,
    ) -> None:
        self.graph = Graph()
        self.ontology_path = ontology_path or settings.ontology_path
        self.data_paths = tuple(data_paths) if data_paths else settings.data_paths
        self._loaded = False

    def load(self) -> "GraphStore":
        """Parse the ontology and all data files into the graph."""
        self.graph.parse(self.ontology_path, format="turtle")
        for path in self.data_paths:
            self.graph.parse(path, format="turtle")
        self._loaded = True
        return self

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Run a SPARQL SELECT/ASK and return rows as a list of dicts.

        Variable names map to their string values; unbound variables are ``None``.
        """
        if not self._loaded:
            self.load()

        result = self.graph.query(sparql)

        # ASK queries return a single boolean.
        if result.type == "ASK":
            return [{"result": bool(result.askAnswer)}]

        rows: list[dict[str, Any]] = []
        for row in result:
            rows.append(
                {
                    str(var): (str(row[var]) if row[var] is not None else None)
                    for var in result.vars
                }
            )
        return rows


def default_store() -> GraphStore:
    """Convenience: a store loaded from the configured ontology + data."""
    return GraphStore().load()
