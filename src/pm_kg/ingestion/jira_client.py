"""JIRA REST client.

STEP 2 (stub). The structure and auth are in place; the network calls are marked
TODO so the scaffold stays runnable without credentials. Fill in `search_issues`
against the JIRA Cloud REST API v3:
    GET /rest/api/3/search?jql=...&fields=...&startAt=...&maxResults=...
Auth is HTTP Basic with (email, api_token).
"""

from __future__ import annotations

from typing import Any, Iterator

from ..config import settings


class JiraClient:
    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.jira_base_url or "").rstrip("/")
        self.email = email or settings.jira_email
        self.api_token = api_token or settings.jira_api_token

    def _require_config(self) -> None:
        missing = [
            name
            for name, value in [
                ("JIRA_BASE_URL", self.base_url),
                ("JIRA_EMAIL", self.email),
                ("JIRA_API_TOKEN", self.api_token),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"Missing JIRA configuration: {', '.join(missing)}. "
                "Set these environment variables (see .env.example)."
            )

    def search_issues(self, jql: str, fields: list[str] | None = None) -> Iterator[dict[str, Any]]:
        """Yield raw JIRA issue JSON objects matching a JQL query.

        TODO(step-2): implement paginated calls to /rest/api/3/search using
        `requests` with HTTP Basic auth (self.email, self.api_token). Yield each
        issue dict; loop until startAt + maxResults >= total.
        """
        self._require_config()
        raise NotImplementedError(
            "JIRA live sync is not implemented yet (step 2). "
            "Use the bundled sample data for now."
        )
