"""Configuration, loaded from environment variables with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Repository root (…/src/pm_kg/config.py -> repo root)
ROOT = Path(__file__).resolve().parents[2]

ONTOLOGY_PATH = ROOT / "ontology" / "pm.ttl"
SAMPLE_DATA_PATH = ROOT / "data" / "sample" / "sample_data.ttl"


@dataclass
class Settings:
    """Runtime settings for the pipeline."""

    # --- LLM ---
    anthropic_api_key: str | None = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    # Default to a current Claude model; override with PMKG_MODEL.
    model: str = field(default_factory=lambda: os.getenv("PMKG_MODEL", "claude-sonnet-5"))
    max_tokens: int = 1500

    # --- Graph store ---
    ontology_path: Path = ONTOLOGY_PATH
    # Comma-separated list of data files to load, or the sample by default.
    data_paths: tuple[Path, ...] = field(
        default_factory=lambda: (
            tuple(Path(p) for p in os.environ["PMKG_DATA"].split(","))
            if os.getenv("PMKG_DATA")
            else (SAMPLE_DATA_PATH,)
        )
    )
    # Optional remote SPARQL endpoint (e.g. Fuseki). If unset, use local rdflib.
    sparql_endpoint: str | None = field(
        default_factory=lambda: os.getenv("PMKG_SPARQL_ENDPOINT")
    )

    # --- JIRA (step 2) ---
    jira_base_url: str | None = field(default_factory=lambda: os.getenv("JIRA_BASE_URL"))
    jira_email: str | None = field(default_factory=lambda: os.getenv("JIRA_EMAIL"))
    jira_api_token: str | None = field(default_factory=lambda: os.getenv("JIRA_API_TOKEN"))


settings = Settings()
