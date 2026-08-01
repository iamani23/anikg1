"""Tests that the ontology + sample data load and answer SPARQL correctly."""

from pm_kg.graph.store import default_store


def test_sample_data_loads():
    store = default_store()
    assert len(store.graph) > 0


def test_open_issues_query():
    store = default_store()
    rows = store.query(
        """
        PREFIX pm: <https://w3id.org/pmkg/ontology#>
        SELECT ?key WHERE {
          ?i pm:issueKey ?key ;
             pm:hasStatus ?s .
          ?s pm:inStatusCategory ?c .
          ?c pm:name ?cat .
          FILTER (?cat != "Done")
        }
        """
    )
    keys = {r["key"] for r in rows}
    # PAY-12 is Done; it should be excluded. The rest are open.
    assert "PAY-12" not in keys
    assert {"PAY-15", "PAY-18", "PAY-20", "PAY-22"}.issubset(keys)


def test_unassigned_bugs():
    store = default_store()
    rows = store.query(
        """
        PREFIX pm: <https://w3id.org/pmkg/ontology#>
        SELECT ?key WHERE {
          ?i a pm:Bug ; pm:issueKey ?key .
          FILTER NOT EXISTS { ?i pm:assignee ?u }
        }
        """
    )
    keys = {r["key"] for r in rows}
    # PAY-18 is an unassigned bug; PAY-15 is a bug assigned to Bob.
    assert keys == {"PAY-18"}


def test_ask_query_returns_boolean():
    store = default_store()
    rows = store.query(
        """
        PREFIX pm: <https://w3id.org/pmkg/ontology#>
        ASK { ?i pm:issueKey "PAY-15" }
        """
    )
    assert rows == [{"result": True}]
