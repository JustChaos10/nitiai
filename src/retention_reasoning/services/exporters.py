"""Exporter stubs for external channels (Klaviyo, MoEngage, etc.)."""

from __future__ import annotations

from typing import Any

from loguru import logger


class KlaviyoExporter:
    def send_campaign(self, campaign: dict[str, Any]) -> dict[str, Any]:
        logger.info("KlaviyoExporter.send_campaign (stub)")
        return {
            "status": "queued",
            "channel": "klaviyo",
            "payload": campaign,
        }


class MoEngageExporter:
    def send_campaign(self, campaign: dict[str, Any]) -> dict[str, Any]:
        logger.info("MoEngageExporter.send_campaign (stub)")
        return {
            "status": "queued",
            "channel": "moengage",
            "payload": campaign,
        }


__all__ = ["KlaviyoExporter", "MoEngageExporter"]
