"""
Retention Reasoning Agent

An explainable AI agent that reasons about retention causes using causal inference.
"""

__version__ = "0.1.0"

from .agent import RetentionReasoningAgent
from .models import (
    Opportunity,
    OpportunityType,
    Hypothesis,
    TestResult,
    CausalStructure,
    Lever,
    InterventionEstimate,
    ReasoningSession,
    ReasoningStep,
    ReasoningChain,
)

__all__ = [
    "RetentionReasoningAgent",
    "Opportunity",
    "OpportunityType",
    "Hypothesis",
    "TestResult",
    "CausalStructure",
    "Lever",
    "InterventionEstimate",
    "ReasoningSession",
    "ReasoningStep",
    "ReasoningChain",
]
