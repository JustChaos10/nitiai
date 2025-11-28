"""Offers agent with heuristic mapping."""

from __future__ import annotations

from typing import Any

from loguru import logger


class OffersAgent:
    """Designs offers with basic structure."""

    def design_offer(self, campaign: dict[str, Any]) -> dict[str, Any]:
        """Return a minimal offer object."""
        logger.info("OffersAgent.design_offer")
        lever = campaign.get("lever", "").lower()
        impact = campaign.get("expected_effect", {}).get("absolute_effect", 0.1) or 0.1

        offer_type = campaign.get("offer_type")
        value = campaign.get("offer_value")
        currency = campaign.get("currency", "USD")

        if not offer_type:
            if "delivery" in lever:
                offer_type = "free_shipping"
                value = 0
            elif "engagement" in lever or "onboarding" in lever:
                offer_type = "bonus_content"
                value = 0
            elif "value" in lever or "price" in lever or "order_value" in lever:
                offer_type = "percent_off"
                value = min(max(int(impact * 20), 5), 15)  # 5-15% cap
            else:
                offer_type = "percent_off"
                value = value or 10

        return {
            "type": offer_type,
            "value": value,
            "currency": currency,
            "notes": "Heuristic offer; replace with pricing logic",
        }
