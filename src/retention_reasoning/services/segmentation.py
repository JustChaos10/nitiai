"""Segmentation agent with simple SQL/attribute generation."""

from __future__ import annotations

from typing import Any

from loguru import logger


class SegmentationAgent:
    """Produces audience definitions and SQL selectors."""

    def _build_where(self, target: str) -> tuple[list[str], list[str]]:
        """Heuristically convert a target expression into WHERE clauses and attributes."""
        where_clauses: list[str] = []
        attrs: list[str] = []
        expr = target.strip()

        # Handle basic comparisons: col OP value
        import re

        m = re.match(r"(?P<col>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>>=|<=|>|<|=)\s*(?P<val>.+)", expr)
        if m:
            col = m.group("col")
            op = m.group("op")
            val = m.group("val").strip()
            attrs.append(col)
            # naïve quoting
            if not val.replace(".", "", 1).isdigit():
                val = val.strip("'\"")
                val = f"'{val}'"
            where_clauses.append(f"{col} {op} {val}")
            return where_clauses, attrs

        # Fallback: just ensure column exists
        col = expr.split()[0]
        attrs.append(col)
        where_clauses.append(f"{col} IS NOT NULL")
        return where_clauses, attrs

    def build_segment(self, campaign: dict[str, Any]) -> dict[str, Any]:
        """Return a segment definition with SQL and attributes."""
        logger.info("SegmentationAgent.build_segment")
        target = campaign.get("lever") or campaign.get("name") or ""
        where_clauses, attrs = self._build_where(target) if target else ([], [])
        target_outcome = campaign.get("target_outcome", "")
        sql = (
            "SELECT customer_id FROM enriched_customers"
            + (f" WHERE {' AND '.join(where_clauses)}" if where_clauses else "")
        )
        return {
            "attributes": campaign.get("segment_attributes", attrs),
            "sql": campaign.get("segment_sql", sql),
            "target_outcome": target_outcome,
            "where_clauses": where_clauses,
        }
