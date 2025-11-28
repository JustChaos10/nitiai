"""Playbook agent with heuristic channel/cadence generation."""

from __future__ import annotations

from typing import Any

from loguru import logger


class PlaybookAgent:
    """Translates campaigns into execution plans."""

    def build_playbook(self, campaign: dict[str, Any]) -> dict[str, Any]:
        """Return a minimal execution plan."""
        logger.info("PlaybookAgent.build_playbook")
        lever = campaign.get("lever", "").lower()
        channels = campaign.get("channels")
        if not channels:
            if "delivery" in lever:
                channels = ["email", "sms"]
            elif "engagement" in lever or "onboarding" in lever:
                channels = ["push", "email"]
            else:
                channels = ["email"]
        cadence = campaign.get("cadence") or ("immediate + day-3 follow-up" if "delivery" in lever else "weekly")
        copy_template = campaign.get("copy_template") or (
            "Address the pain point, provide reassurance, and a clear next step."
        )
        return {
            "channels": channels,
            "cadence": cadence,
            "copy_template": copy_template,
            "notes": "Heuristic playbook; replace with channel-specific logic",
        }
