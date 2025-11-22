"""Config helpers for environment-driven settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load .env if present
load_dotenv()


@dataclass
class BigQueryConfig:
    project_id: Optional[str] = os.getenv("BQ_PROJECT_ID")
    dataset: Optional[str] = os.getenv("BQ_DATASET")
    table: str = os.getenv("BQ_CUSTOMERS_TABLE", "enriched_customers")


@dataclass
class AgentConfig:
    max_rows: int = int(os.getenv("AGENT_MAX_ROWS", "5000"))

