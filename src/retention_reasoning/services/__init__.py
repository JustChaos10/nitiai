"""Service stubs for downstream agents (segmentation, offers, playbook, performance)."""

from .segmentation import SegmentationAgent
from .offers import OffersAgent
from .playbook import PlaybookAgent
from .performance import PerformanceAgent
from .strategy import StrategyComposer
from .exporters import KlaviyoExporter, MoEngageExporter
from .ab_testing import ABTestRecommender, ABTestDesign

__all__ = [
    "SegmentationAgent",
    "OffersAgent",
    "PlaybookAgent",
    "PerformanceAgent",
    "StrategyComposer",
    "KlaviyoExporter",
    "MoEngageExporter",
    "ABTestRecommender",
    "ABTestDesign",
]
