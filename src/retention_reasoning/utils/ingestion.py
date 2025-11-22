"""Ingestion stubs for alerts/insights into Opportunities."""

from __future__ import annotations

from typing import Any, Mapping

from loguru import logger

from ..models.opportunity import Opportunity, OpportunityType


class AlertIngestionService:
    """Transforms incoming alerts/insights into Opportunity objects."""

    def from_payload(self, payload: Mapping[str, Any]) -> Opportunity:
        """Convert a generic alert payload to an Opportunity.

        Expected payload keys (minimal): title, description, metric_name, baseline_value, current_value, sample_size, severity.
        """
        logger.info("Creating Opportunity from alert payload")
        return Opportunity(
            type=OpportunityType(payload.get("type", OpportunityType.CHURN_SPIKE)),
            title=payload.get("title", "Unspecified Opportunity"),
            description=payload.get("description", "No description provided"),
            affected_cohort=payload.get("cohort", {}),
            metric_name=payload.get("metric_name", "churn_30d"),
            baseline_value=float(payload.get("baseline_value", 0.0)),
            current_value=float(payload.get("current_value", 0.0)),
            sample_size=int(payload.get("sample_size", 0)),
            severity=payload.get("severity", "medium"),
            business_context=payload.get("business_context", {}),
        )

