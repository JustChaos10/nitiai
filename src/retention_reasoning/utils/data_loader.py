"""Data loading utilities for external stores (e.g., BigQuery)."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from loguru import logger

from .config import BigQueryConfig


class BigQueryLoader:
    """Lightweight BigQuery loader wrapper.

    This keeps imports optional to avoid hard dependency at import time.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset: Optional[str] = None,
        credentials: Any = None,
        table: str | None = None,
    ) -> None:
        cfg = BigQueryConfig()
        self.project_id = project_id or cfg.project_id
        self.dataset = dataset or cfg.dataset
        self.credentials = credentials
        self.table = table or cfg.table
        self._client = None

    def _ensure_client(self):
        if self._client:
            return self._client
        try:
            from google.cloud import bigquery  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise ImportError(
                "google-cloud-bigquery is required. Install with: pip install google-cloud-bigquery"
            ) from exc

        self._client = bigquery.Client(
            project=self.project_id, credentials=self.credentials
        )
        return self._client

    def load_table(self, table: str, where: str | None = None, limit: int | None = None) -> pd.DataFrame:
        """Load a table (optionally filtered) into a DataFrame."""
        client = self._ensure_client()
        fq_table = table if "." in table else f"{self.project_id}.{self.dataset}.{table}"
        query = f"SELECT * FROM `{fq_table}`"
        if where:
            query += f" WHERE {where}"
        if limit:
            query += f" LIMIT {limit}"
        logger.info(f"Executing BigQuery: {query}")
        job = client.query(query)
        return job.result().to_dataframe()

    def load_enriched_customers(
        self,
        where: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Convenience loader for the enriched_customers table."""
        target_table = self.table or "enriched_customers"
        return self.load_table(target_table, where=where, limit=limit)


def load_feature_metadata(source: Any) -> list[dict[str, Any]]:
    """Load feature metadata from a list/dict or JSON file path."""
    if source is None:
        logger.info("No feature metadata source provided; returning empty list")
        return []

    if isinstance(source, (list, tuple)):
        return list(source)

    if isinstance(source, str):
        import json
        logger.info(f"Loading feature metadata from file: {source}")
        with open(source, "r", encoding="utf-8") as f:
            return json.load(f)

    if isinstance(source, dict):
        return [source]

    logger.warning("Unknown feature metadata source type; returning empty list")
    return []
