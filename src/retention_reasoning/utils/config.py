"""Config helpers for environment-driven settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load .env if present
load_dotenv()


@dataclass
class AgentConfig:
    max_rows: int = int(os.getenv("AGENT_MAX_ROWS", "5000"))

