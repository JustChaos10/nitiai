"""Strategy composer that combines levers with segmentation, offers, and playbooks."""

from __future__ import annotations

from typing import Any, List

from loguru import logger

from .segmentation import SegmentationAgent
from .offers import OffersAgent
from .playbook import PlaybookAgent
from .performance import PerformanceAgent


class StrategyComposer:
    """Compose campaigns from levers and downstream agent stubs."""

    def __init__(
        self,
        segmentation_agent: SegmentationAgent | None = None,
        offers_agent: OffersAgent | None = None,
        playbook_agent: PlaybookAgent | None = None,
        performance_agent: PerformanceAgent | None = None,
    ) -> None:
        self.segmentation_agent = segmentation_agent or SegmentationAgent()
        self.offers_agent = offers_agent or OffersAgent()
        self.playbook_agent = playbook_agent or PlaybookAgent()
        self.performance_agent = performance_agent or PerformanceAgent()

    def compose_campaigns(self, levers: List[Any]) -> list[dict[str, Any]]:
        """Create simple campaign objects from levers."""
        campaigns: list[dict[str, Any]] = []
        for lever in levers:
            logger.info(f"Composing campaign for lever {lever.name}")
            base_campaign = {
                "name": f"Act on {lever.target_variable}",
                "target_outcome": lever.target_outcome,
                "lever": lever.name,
                "mechanism": lever.mechanism,
                "expected_effect": lever.expected_effect.model_dump(),
            }

            segment = self.segmentation_agent.build_segment(base_campaign)
            offer = self.offers_agent.design_offer(base_campaign)
            playbook = self.playbook_agent.build_playbook(base_campaign)
            performance = self.performance_agent.grade_performance(
                {
                    "lift": lever.expected_effect.absolute_effect if lever.expected_effect else 0.0,
                    "roi": lever.expected_effect.relative_effect if lever.expected_effect else 0.0,
                    "sample_size": lever.expected_effect.affected_customers if lever.expected_effect else 0,
                    "redemption_rate": 0.0,
                }
            )

            campaigns.append(
                {
                    **base_campaign,
                    "segment": segment,
                    "offer": offer,
                    "playbook": playbook,
                    "performance": performance,
                }
            )
        return campaigns
